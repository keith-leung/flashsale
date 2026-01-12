using AutoMapper;
using FlashSale.Api.Data;
using FlashSale.Api.DTOs;
using FlashSale.Api.Models;
using FlashSaleAPI.Services;
using Microsoft.EntityFrameworkCore;

namespace FlashSale.Api.Services;

public class OrderService : IOrderService
{
    private readonly FlashSaleDbContext _context;
    private readonly IMapper _mapper;
    private readonly ILogger<OrderService> _logger;
    private readonly CSharpSnowflakeGenerator _idGenerator;
    private readonly RedisCacheService _redisCache;
    private readonly CampaignMemoryAllocator _campaignAllocator;

    public OrderService(FlashSaleDbContext context, IMapper mapper, ILogger<OrderService> logger, CSharpSnowflakeGenerator idGenerator, RedisCacheService redisCache, CampaignMemoryAllocator campaignAllocator)
    {
        _context = context;
        _mapper = mapper;
        _logger = logger;
        _idGenerator = idGenerator;
        _redisCache = redisCache;
        _campaignAllocator = campaignAllocator;
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
    /// Variant A: Dual-layer inventory with preallocated memory (99%+ zero network I/O)
    ///
    /// Architecture:
    /// - Layer 1: SPU counter (campaign-wide limit) - enforces total campaign limit
    /// - Layer 2: SKU caches (per-SKU inventory) - tracks individual variants
    ///
    /// Flow: Check SPU counter → decrement → check SKU cache → decrement → success
    /// If SPU depleted: async refill from Redis pool (non-blocking)
    ///
    /// Orders queue to Redis for write-back AFTER campaign ends.
    /// </summary>
    private async Task<OrderResponseDto> CreateOrderVariantAAsync(OrderCreateDto dto, string orderNumber, Guid flashSaleId)
    {
        _logger.LogDebug("Variant A (Dual-Layer) for order {OrderNumber}, campaign {FlashSaleId}", orderNumber, flashSaleId);

        // Reserve each SKU using dual-layer CampaignMemoryAllocator
        // SPU counter (Layer 1) ensures campaign-wide limit
        // SKU cache (Layer 2) tracks per-SKU inventory
        var reservedItems = new List<(Guid SkuId, int Quantity, decimal UnitPrice)>();
        decimal subtotal = 0;

        try
        {
            foreach (var itemDto in dto.LineItems)
            {
                decimal itemPrice = 0;
                decimal itemSubtotal = 0;

                // Reserve items using dual-layer allocator (one at a time for quantity > 1)
                for (int i = 0; i < itemDto.Quantity; i++)
                {
                    var result = _campaignAllocator.ReserveItem(flashSaleId, itemDto.SkuId);

                    if (!result.Success)
                    {
                        switch (result.PriceType)
                        {
                            case "sold_out":
                                _logger.LogWarning("SKU {SkuId} sold out in campaign {CampaignId}", itemDto.SkuId, flashSaleId);
                                throw new InvalidOperationException($"SKU {itemDto.SkuId} sold out");

                            case "not_allocated":
                                _logger.LogWarning("SKU {SkuId} not allocated to this node", itemDto.SkuId);
                                throw new InvalidOperationException($"SKU {itemDto.SkuId} not available on this server");

                            default:
                                _logger.LogError("Reservation failed for SKU {SkuId}: {PriceType}", itemDto.SkuId, result.PriceType);
                                throw new InvalidOperationException($"Failed to reserve SKU {itemDto.SkuId}");
                        }
                    }

                    // Check if fell back to ordinary stock (benchmark stop indicator)
                    if (result.PriceType == "ordinary")
                    {
                        _logger.LogWarning("[BENCHMARK STOP] SKU {SkuId} using ordinary price", itemDto.SkuId);
                    }

                    // Capture the price from first successful reservation
                    if (i == 0)
                    {
                        itemPrice = result.Price;
                    }
                    itemSubtotal += result.Price;
                }

                subtotal += itemSubtotal;
                reservedItems.Add((itemDto.SkuId, itemDto.Quantity, itemPrice));
            }

            // Queue order for async write-back (after campaign ends)
            var lineItemsPayload = reservedItems.Select(item => new Dictionary<string, object>
            {
                ["sku_id"] = item.SkuId.ToString(),
                ["quantity"] = item.Quantity,
                ["unit_price"] = item.UnitPrice.ToString("F2")
            }).ToList();

            var orderPayload = new Dictionary<string, object>
            {
                ["order_number"] = orderNumber,
                ["customer_email"] = dto.CustomerEmail,
                ["customer_name"] = dto.CustomerName ?? "",
                ["flash_sale_id"] = flashSaleId.ToString(),
                ["line_items"] = lineItemsPayload,
                ["subtotal"] = subtotal.ToString("F2"),
                ["created_at"] = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
            };

            await _redisCache.QueueOrderAsync(orderPayload);

            _logger.LogDebug("Order {OrderNumber} reserved (Variant A dual-layer), queued for write-back", orderNumber);

            return new OrderResponseDto
            {
                OrderNumber = orderNumber,
                CustomerEmail = dto.CustomerEmail,
                CustomerName = dto.CustomerName,
                FlashSaleCampaignId = flashSaleId,
                Status = OrderStatus.Pending,
                Subtotal = subtotal,
                TotalAmount = subtotal + dto.TaxAmount + dto.ShippingAmount
            };
        }
        catch (Exception ex)
        {
            // Note: Dual-layer doesn't support easy rollback (items consumed from local cache)
            // In production, implement compensation or accept small variance
            _logger.LogError(ex, "Order {OrderNumber} failed in Variant A", orderNumber);
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
