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
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Instant;
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
    private final SnowflakeIdGenerator idGenerator;
    private final RedisCacheService redisCache;

    @Autowired
    public OrderService(
            OrderRepository orderRepository,
            OrderLineItemRepository orderLineItemRepository,
            PaymentRepository paymentRepository,
            SkuRepository skuRepository,
            InventoryRepository inventoryRepository,
            SnowflakeIdGenerator idGenerator,
            RedisCacheService redisCache) {
        this.orderRepository = orderRepository;
        this.orderLineItemRepository = orderLineItemRepository;
        this.paymentRepository = paymentRepository;
        this.skuRepository = skuRepository;
        this.inventoryRepository = inventoryRepository;
        this.idGenerator = idGenerator;
        this.redisCache = redisCache;
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
     * - If SKU is in active flash sale campaign → Use Variant X (Redis atomic counters)
     * - Otherwise → Use Variant Y (database transaction)
     * Frontend sees same API, backend handles routing transparently.
     */
    public OrderResponseDto createOrder(OrderCreateDto createDto) {
        String orderNumber = String.format("ORD-%d", idGenerator.generate());

        // Step 1: Check if ANY SKU is in active flash sale campaign
        List<UUID> skuIds = createDto.getLineItems().stream()
                .map(OrderLineItemCreateDto::getSkuId)
                .collect(Collectors.toList());

        UUID flashSaleId = null;
        boolean useVariantX = false;

        for (UUID skuId : skuIds) {
            Map<String, String> meta = redisCache.getSkuMeta(skuId);
            if (meta != null && meta.get("flash_sale_id") != null && "active".equals(meta.get("status"))) {
                flashSaleId = UUID.fromString(meta.get("flash_sale_id"));
                useVariantX = true;
                break;
            }
        }

        if (useVariantX) {
            // VARIANT X: Redis Atomic Counters (Flash Sale Path)
            return createOrderVariantX(createDto, orderNumber, flashSaleId);
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
        order.setFlashSaleId(createDto.getFlashSaleId());

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

            // Create line item
            BigDecimal unitPrice = itemDto.getUnitPrice() != null ? itemDto.getUnitPrice() : sku.getPrice();
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
     * Variant X: Redis atomic counters path (0 database queries during flash sale).
     * Used when SKU is in active flash sale campaign.
     */
    private OrderResponseDto createOrderVariantX(OrderCreateDto createDto, String orderNumber, UUID flashSaleId) {
        // Step 1: Reserve from campaign limit
        int totalQuantity = createDto.getLineItems().stream()
                .mapToInt(OrderLineItemCreateDto::getQuantity)
                .sum();

        Long campaignRemaining = redisCache.reserveCampaignInventory(flashSaleId, totalQuantity);
        if (campaignRemaining < 0) {
            throw new IllegalStateException("Flash sale campaign sold out");
        }

        // Step 2: Reserve each SKU inventory
        List<Map.Entry<UUID, Integer>> reservedSkus = new ArrayList<>();

        try {
            for (OrderLineItemCreateDto itemDto : createDto.getLineItems()) {
                Long skuRemaining = redisCache.reserveSkuInventory(itemDto.getSkuId(), itemDto.getQuantity());

                if (skuRemaining < 0) {
                    // Rollback: Release all reserved inventory
                    for (Map.Entry<UUID, Integer> entry : reservedSkus) {
                        redisCache.releaseSkuInventory(entry.getKey(), entry.getValue());
                    }
                    redisCache.releaseCampaignInventory(flashSaleId, totalQuantity);

                    throw new IllegalStateException("SKU " + itemDto.getSkuId() + " sold out");
                }

                reservedSkus.add(new AbstractMap.SimpleEntry<>(itemDto.getSkuId(), itemDto.getQuantity()));
            }

            // Step 3: Queue order for async database persistence
            Map<String, Object> orderPayload = new HashMap<>();
            orderPayload.put("order_number", orderNumber);
            orderPayload.put("customer_email", createDto.getCustomerEmail());
            orderPayload.put("customer_name", createDto.getCustomerName() != null ? createDto.getCustomerName() : "");
            orderPayload.put("flash_sale_id", flashSaleId.toString());

            List<Map<String, Object>> lineItems = new ArrayList<>();
            for (OrderLineItemCreateDto itemDto : createDto.getLineItems()) {
                Map<String, Object> lineItem = new HashMap<>();
                lineItem.put("sku_id", itemDto.getSkuId().toString());
                lineItem.put("quantity", itemDto.getQuantity());

                Map<String, String> skuMeta = redisCache.getSkuMeta(itemDto.getSkuId());
                lineItem.put("unit_price", skuMeta != null ? skuMeta.get("price") : "0");

                lineItems.add(lineItem);
            }
            orderPayload.put("line_items", lineItems);

            redisCache.queueOrder(orderPayload);

            // Step 4: Build response (order will be persisted async)
            OrderResponseDto response = new OrderResponseDto();
            response.setOrderNumber(orderNumber);
            response.setCustomerEmail(createDto.getCustomerEmail());
            response.setCustomerName(createDto.getCustomerName());
            response.setFlashSaleId(flashSaleId);
            response.setStatus(OrderStatus.pending);

            return response;

        } catch (Exception e) {
            // Rollback all reservations on error
            for (Map.Entry<UUID, Integer> entry : reservedSkus) {
                redisCache.releaseSkuInventory(entry.getKey(), entry.getValue());
            }
            redisCache.releaseCampaignInventory(flashSaleId, totalQuantity);
            throw e;
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
        dto.setFlashSaleId(order.getFlashSaleId());
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
