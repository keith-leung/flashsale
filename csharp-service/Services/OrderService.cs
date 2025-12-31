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

    public OrderService(FlashSaleDbContext context, IMapper mapper, ILogger<OrderService> logger, CSharpSnowflakeGenerator idGenerator, RedisCacheService redisCache)
    {
        _context = context;
        _mapper = mapper;
        _logger = logger;
        _idGenerator = idGenerator;
        _redisCache = redisCache;
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
    /// - If SKU is in active flash sale campaign → Use Variant X (Redis atomic counters)
    /// - Otherwise → Use Variant Y (database transaction)
    /// Frontend sees same API, backend handles routing transparently.
    /// </summary>
    public async Task<OrderResponseDto> CreateAsync(OrderCreateDto dto)
    {
        var orderNumber = $"ORD-{_idGenerator.Generate()}";

        // Step 1: Check if ANY SKU is in active flash sale campaign
        var skuIds = dto.LineItems.Select(item => item.SkuId).ToList();

        Guid? flashSaleId = null;
        bool useVariantX = false;

        foreach (var skuId in skuIds)
        {
            var meta = await _redisCache.GetSkuMetaAsync(skuId);
            if (meta != null && meta.ContainsKey("flash_sale_id") && meta.GetValueOrDefault("status") == "active")
            {
                flashSaleId = Guid.Parse(meta["flash_sale_id"]);
                useVariantX = true;
                _logger.LogInformation("SKU {SkuId} is in active flash sale {FlashSaleId}, using Variant X", skuId, flashSaleId);
                break;
            }
        }

        if (useVariantX && flashSaleId.HasValue)
        {
            // VARIANT X: Redis Atomic Counters (Flash Sale Path)
            return await CreateOrderVariantXAsync(dto, orderNumber, flashSaleId.Value);
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
                Notes = dto.Notes
                // flash_sale_campaign_id will be set automatically if SKU is in active campaign
            };

            _context.Orders.Add(order);
            await _context.SaveChangesAsync(); // Get the order ID

            // Track active campaign for this order (if any)
            FlashSaleCampaign? activeCampaign = null;

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

                // DUAL VALIDATION: Check for active flash sale campaign on this SKU's SPU
                if (sku.SpuId != null)
                {
                    var now = DateTime.UtcNow;
                    var campaign = await _context.FlashSaleCampaigns
                        .FirstOrDefaultAsync(c =>
                            c.SpuId == sku.SpuId &&
                            c.IsActive == true &&
                            c.Status == FlashSaleStatus.Active &&
                            c.StartTime <= now &&
                            c.EndTime >= now);

                    if (campaign != null)
                    {
                        // SPU-level validation: Check campaign limit
                        if (campaign.SoldQuantity + itemDto.Quantity > campaign.TotalSaleLimit)
                        {
                            throw new InvalidOperationException(
                                $"Flash sale campaign '{campaign.Name}' limit exceeded. Only {campaign.TotalSaleLimit - campaign.SoldQuantity} items remaining.");
                        }

                        // Store campaign reference for order
                        activeCampaign = campaign;

                        // Atomically increment campaign sold_quantity
                        campaign.SoldQuantity += itemDto.Quantity;

                        // Update campaign status if sold out
                        if (campaign.SoldQuantity >= campaign.TotalSaleLimit)
                        {
                            campaign.Status = FlashSaleStatus.Ended;
                        }
                    }
                }

                // SKU-level validation: Check inventory
                if (sku.TrackInventory && sku.Inventory != null)
                {
                    if (!sku.Inventory.CanFulfillQuantity(itemDto.Quantity))
                    {
                        throw new InvalidOperationException($"Insufficient inventory for SKU {sku.SkuCode}");
                    }

                    // Reserve inventory
                    sku.Inventory.ReserveQuantity(itemDto.Quantity);
                }

                // Create line item
                var unitPrice = itemDto.UnitPrice ?? sku.Price;
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

            // Link order to campaign if it was part of a flash sale
            if (activeCampaign != null)
            {
                order.FlashSaleCampaignId = activeCampaign.Id;
            }

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
    /// Variant X: Redis atomic counters path (0 database queries during flash sale).
    /// Used when SKU is in active flash sale campaign.
    /// </summary>
    private async Task<OrderResponseDto> CreateOrderVariantXAsync(OrderCreateDto dto, string orderNumber, Guid flashSaleId)
    {
        _logger.LogInformation("Using Variant X (Redis) for order {OrderNumber}, flash sale {FlashSaleId}", orderNumber, flashSaleId);

        // Step 1: Reserve from campaign limit
        var totalQuantity = dto.LineItems.Sum(item => item.Quantity);
        var campaignRemaining = await _redisCache.ReserveCampaignInventoryAsync(flashSaleId, totalQuantity);

        if (campaignRemaining < 0)
        {
            _logger.LogWarning("Campaign {FlashSaleId} sold out, remaining: {Remaining}", flashSaleId, campaignRemaining);
            throw new InvalidOperationException("Flash sale campaign sold out");
        }

        // Step 2: Reserve each SKU inventory
        var reservedSkus = new List<(Guid SkuId, int Quantity)>();

        try
        {
            foreach (var itemDto in dto.LineItems)
            {
                var skuRemaining = await _redisCache.ReserveSkuInventoryAsync(itemDto.SkuId, itemDto.Quantity);

                if (skuRemaining < 0)
                {
                    // Rollback: Release all reserved inventory
                    foreach (var (skuId, quantity) in reservedSkus)
                    {
                        await _redisCache.ReleaseSkuInventoryAsync(skuId, quantity);
                    }
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
            _logger.LogInformation("Order {OrderNumber} reserved successfully (Variant X), queued for persistence", orderNumber);

            return new OrderResponseDto
            {
                OrderNumber = orderNumber,
                CustomerEmail = dto.CustomerEmail,
                CustomerName = dto.CustomerName,
                FlashSaleId = flashSaleId,
                Status = OrderStatus.Pending
            };
        }
        catch
        {
            // Rollback all reservations on error
            foreach (var (skuId, quantity) in reservedSkus)
            {
                await _redisCache.ReleaseSkuInventoryAsync(skuId, quantity);
            }
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
