using AutoMapper;
using FlashSale.Api.Data;
using FlashSale.Api.DTOs;
using FlashSale.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace FlashSale.Api.Services;

public class OrderService : IOrderService
{
    private readonly FlashSaleDbContext _context;
    private readonly IMapper _mapper;
    private readonly ILogger<OrderService> _logger;
    private readonly CSharpSnowflakeGenerator _idGenerator;
    private readonly RedisCacheService _redisCache;
    private readonly AllocationManagerV2 _allocationManager;

    public OrderService(FlashSaleDbContext context, IMapper mapper, ILogger<OrderService> logger, CSharpSnowflakeGenerator idGenerator, RedisCacheService redisCache, AllocationManagerV2 allocationManager)
    {
        _context = context;
        _mapper = mapper;
        _logger = logger;
        _idGenerator = idGenerator;
        _redisCache = redisCache;
        _allocationManager = allocationManager;
    }

    public async Task<IEnumerable<OrderResponseDto>> GetAllAsync(int skip = 0, int take = 100, string? customerEmail = null)
    {
        var query = _context.Orders
            .Include(o => o.LineItems)
            .Include(o => o.FlashSaleCampaign)
            .AsQueryable();

        if (!string.IsNullOrEmpty(customerEmail))
        {
            query = query.Where(o => o.CustomerEmail.Contains(customerEmail));
        }

        var orders = await query
            .OrderByDescending(o => o.CreatedAt)
            .Skip(skip)
            .Take(take)
            .ToListAsync();

        return _mapper.Map<IEnumerable<OrderResponseDto>>(orders);
    }

    public async Task<OrderResponseDto?> GetByIdAsync(Guid id)
    {
        var order = await _context.Orders
            .Include(o => o.LineItems)
            .Include(o => o.FlashSaleCampaign)
            .FirstOrDefaultAsync(o => o.Id == id);

        return order == null ? null : _mapper.Map<OrderResponseDto>(order);
    }

    /// <summary>
    /// Create order with intelligent routing:
    /// - If SKU is in active flash sale campaign → Use Variant A (Allocation-based adaptive inventory)
    /// - Otherwise → Use Variant Y (database transaction)
    /// Frontend sees same API, backend handles routing transparently.
    /// </summary>
    public async Task<OrderResponseDto> CreateAsync(OrderCreateDto dto)
    {
        var orderNumber = $"ORD-{_idGenerator.Generate()}";

        // Step 1: Check if ANY SKU is in active flash sale campaign
        var skuIds = dto.LineItems.Select(item => item.SkuId).ToList();

        Guid? flashSaleId = null;
        bool useVariantA = false;

        foreach (var skuId in skuIds)
        {
            var meta = await _redisCache.GetSkuMetaAsync(skuId);
            if (meta != null && meta.ContainsKey("flash_sale_id") && meta.GetValueOrDefault("status") == "active")
            {
                flashSaleId = Guid.Parse(meta["flash_sale_id"]);
                useVariantA = true;
                _logger.LogInformation("SKU {SkuId} is in active flash sale {FlashSaleId}, using Variant A", skuId, flashSaleId);
                break;
            }
        }

        if (useVariantA && flashSaleId.HasValue)
        {
            // VARIANT A: Allocation-based Adaptive Inventory (Flash Sale Path)
            return await CreateOrderVariantAAsync(dto, orderNumber, flashSaleId.Value);
        }
        else
        {
            // VARIANT Y: Database Transaction (Regular Order Path)
            return await CreateOrderVariantYAsync(dto, orderNumber);
        }
    }

    /// <summary>
    /// Variant Y: Traditional database transaction path (4-7 queries per order).
    /// Used for regular orders when SKU is NOT in active flash sale.
    /// </summary>
    private async Task<OrderResponseDto> CreateOrderVariantYAsync(OrderCreateDto dto, string orderNumber)
    {
        using var transaction = await _context.Database.BeginTransactionAsync();

        try
        {
            _logger.LogInformation("Using Variant Y (database) for order {OrderNumber}", orderNumber);

            // Create order
            var order = new Order
            {
                OrderNumber = orderNumber,
                CustomerEmail = dto.CustomerEmail,
                CustomerName = dto.CustomerName,
                TaxAmount = dto.TaxAmount,
                ShippingAmount = dto.ShippingAmount,
                Currency = dto.Currency,
                Notes = dto.Notes,
                FlashSaleCampaignId = dto.FlashSaleCampaignId
            };

            _context.Orders.Add(order);
            await _context.SaveChangesAsync(); // Get the order ID

            // Add line items and calculate totals
            decimal subtotal = 0;
            foreach (var itemDto in dto.LineItems)
            {
                // Get SKU information
                var sku = await _context.Skus
                    .Include(s => s.Inventory)
                    .Include(s => s.Spu)
                    .FirstOrDefaultAsync(s => s.Id == itemDto.SkuId);

                if (sku == null)
                {
                    throw new InvalidOperationException($"SKU {itemDto.SkuId} not found");
                }

                // Check inventory
                if (sku.TrackInventory && sku.Inventory != null)
                {
                    if (!sku.Inventory.CanFulfillQuantity(itemDto.Quantity))
                    {
                        throw new InvalidOperationException($"Insufficient inventory for SKU {sku.SkuCode}");
                    }

                    // Reserve inventory
                    sku.Inventory.ReserveQuantity(itemDto.Quantity);
                }

                // Check for active flash sale campaign and apply flash price
                Models.FlashSale? activeCampaign = null;
                if (sku.SpuId != null)
                {
                    var now = DateTime.UtcNow;
                    activeCampaign = await _context.FlashSaleCampaigns
                        .FirstOrDefaultAsync(c =>
                            c.SpuId == sku.SpuId &&
                            c.IsActive &&
                            c.Status == "active" &&
                            c.StartTime <= now &&
                            c.EndTime >= now);
                }

                // Create line item - use flash price if campaign is active
                var unitPrice = activeCampaign != null
                    ? (itemDto.UnitPrice ?? activeCampaign.FlashPrice)
                    : (itemDto.UnitPrice ?? sku.Price);
                var totalPrice = unitPrice * itemDto.Quantity;

                var lineItem = new OrderLineItem
                {
                    OrderId = order.Id,
                    SkuId = sku.Id,
                    Quantity = itemDto.Quantity,
                    UnitPrice = unitPrice,
                    TotalPrice = totalPrice,
                    ProductName = sku.Spu?.Name ?? sku.Name ?? "Product",
                    SkuCode = sku.SkuCode
                };

                _context.OrderLineItems.Add(lineItem);
                subtotal += totalPrice;
            }

            // Update order totals
            order.Subtotal = subtotal;
            order.TotalAmount = subtotal + order.TaxAmount + order.ShippingAmount;

            await _context.SaveChangesAsync();
            await transaction.CommitAsync();

            _logger.LogInformation("Created order {OrderNumber} for {CustomerEmail} (Variant Y)", orderNumber, dto.CustomerEmail);

            // Return the created order with line items
            var createdOrder = await GetByIdAsync(order.Id);
            return createdOrder!;
        }
        catch
        {
            await transaction.RollbackAsync();
            throw;
        }
    }

    /// <summary>
    /// Variant A: Allocation-based adaptive inventory with async refills
    /// Uses database allocation units loaded into RAM (99%+ network I/O reduction)
    /// Used when SKU is in active flash sale campaign.
    /// </summary>
    private async Task<OrderResponseDto> CreateOrderVariantAAsync(OrderCreateDto dto, string orderNumber, Guid flashSaleId)
    {
        _logger.LogInformation("Using Variant A (Adaptive) for order {OrderNumber}, flash sale {FlashSaleId}", orderNumber, flashSaleId);

        // Step 1: Reserve from campaign limit (still needed at campaign level)
        var totalQuantity = dto.LineItems.Sum(item => item.Quantity);
        var campaignRemaining = await _redisCache.ReserveCampaignInventoryAsync(flashSaleId, totalQuantity);

        if (campaignRemaining < 0)
        {
            _logger.LogWarning("Campaign {FlashSaleId} sold out, remaining: {Remaining}", flashSaleId, campaignRemaining);
            throw new InvalidOperationException("Flash sale campaign sold out");
        }

        // Step 2: Reserve each SKU inventory using Adaptive Inventory Service
        var reservedSkus = new List<(Guid SkuId, int Quantity)>();

        try
        {
            foreach (var itemDto in dto.LineItems)
            {
                // Get adaptive inventory manager for this SKU (allocation-based)
                var inventory = _allocationManager.GetInventoryForSku(itemDto.SkuId);

                if (inventory == null)
                {
                    // This service instance doesn't have allocation units for this SKU
                    // Fall back to direct Redis campaign pool
                    _logger.LogWarning("No allocation units for SKU {SkuId}, using fallback", itemDto.SkuId);

                    // Already reserved from campaign pool above, so just continue
                    reservedSkus.Add((itemDto.SkuId, itemDto.Quantity));
                    continue;
                }

                // Reserve items using allocation-based adaptive inventory
                bool reserved = true;
                for (int i = 0; i < itemDto.Quantity; i++)
                {
                    var (success, priceType, price) = await inventory.ReserveItemAsync();
                    if (!success)
                    {
                        reserved = false;
                        break;
                    }
                }

                if (!reserved)
                {
                    // Rollback campaign inventory on error
                    await _redisCache.ReleaseCampaignInventoryAsync(flashSaleId, totalQuantity);

                    throw new InvalidOperationException($"SKU {itemDto.SkuId} sold out");
                }

                reservedSkus.Add((itemDto.SkuId, itemDto.Quantity));
            }

            // Step 3: Queue order for async database persistence
            var lineItems = new List<Dictionary<string, object>>();

            foreach (var itemDto in dto.LineItems)
            {
                var skuMeta = await _redisCache.GetSkuMetaAsync(itemDto.SkuId);
                lineItems.Add(new Dictionary<string, object>
                {
                    ["sku_id"] = itemDto.SkuId.ToString(),
                    ["quantity"] = itemDto.Quantity,
                    ["unit_price"] = skuMeta?.GetValueOrDefault("price", "0") ?? "0"
                });
            }

            var orderPayload = new Dictionary<string, object>
            {
                ["order_number"] = orderNumber,
                ["customer_email"] = dto.CustomerEmail,
                ["customer_name"] = dto.CustomerName ?? "",
                ["flash_sale_id"] = flashSaleId.ToString(),
                ["line_items"] = lineItems
            };

            await _redisCache.QueueOrderAsync(orderPayload);

            // Step 4: Build response (order will be persisted async)
            _logger.LogInformation("Order {OrderNumber} reserved successfully (Variant A), queued for persistence", orderNumber);

            return new OrderResponseDto
            {
                OrderNumber = orderNumber,
                CustomerEmail = dto.CustomerEmail,
                CustomerName = dto.CustomerName,
                FlashSaleCampaignId = flashSaleId,
                Status = OrderStatus.Pending
            };
        }
        catch
        {
            // Rollback campaign inventory on error
            // Note: Adaptive inventory doesn't support easy rollback (items consumed from local cache)
            // In production, implement compensation logic or accept small inventory variance
            await _redisCache.ReleaseCampaignInventoryAsync(flashSaleId, totalQuantity);
            throw;
        }
    }

    public async Task<OrderResponseDto?> UpdateStatusAsync(Guid id, string status)
    {
        var order = await _context.Orders.FindAsync(id);
        if (order == null) return null;

        if (!Enum.TryParse<OrderStatus>(status, true, out var orderStatus))
        {
            throw new InvalidOperationException($"Invalid order status: {status}");
        }

        order.Status = orderStatus;
        await _context.SaveChangesAsync();

        _logger.LogInformation("Updated order {OrderId} status to {Status}", id, status);
        
        return await GetByIdAsync(id);
    }

    public async Task<bool> CancelAsync(Guid id)
    {
        var order = await _context.Orders
            .Include(o => o.LineItems)
            .FirstOrDefaultAsync(o => o.Id == id);
            
        if (order == null) return false;

        // Release reserved inventory
        foreach (var lineItem in order.LineItems)
        {
            var inventory = await _context.Inventories
                .FirstOrDefaultAsync(i => i.SkuId == lineItem.SkuId);
            inventory?.ReleaseQuantity(lineItem.Quantity);
        }

        order.Status = OrderStatus.Cancelled;
        await _context.SaveChangesAsync();

        _logger.LogInformation("Cancelled order {OrderId}", id);
        
        return true;
    }

    public async Task<PaymentResponseDto> CreatePaymentAsync(Guid orderId, PaymentCreateDto dto)
    {
        var order = await _context.Orders.FindAsync(orderId);
        if (order == null)
        {
            throw new InvalidOperationException("Order not found");
        }

        var payment = new Payment
        {
            OrderId = orderId,
            Amount = dto.Amount,
            Currency = dto.Currency,
            PaymentMethod = dto.PaymentMethod,
            ReferenceNumber = dto.ReferenceNumber,
            Notes = dto.Notes
        };

        // Simulate payment processing
        if (dto.Amount > 0)
        {
            payment.Status = PaymentStatus.Captured;
            payment.GatewayTransactionId = $"txn_{DateTimeOffset.UtcNow.ToUnixTimeSeconds()}";
            
            // Update order status
            order.Status = OrderStatus.Confirmed;
        }

        _context.Payments.Add(payment);
        await _context.SaveChangesAsync();

        _logger.LogInformation("Created payment {PaymentId} for order {OrderId}", payment.Id, orderId);

        return _mapper.Map<PaymentResponseDto>(payment);
    }
}
