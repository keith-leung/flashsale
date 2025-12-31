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

    public OrderService(FlashSaleDbContext context, IMapper mapper, ILogger<OrderService> logger, CSharpSnowflakeGenerator idGenerator)
    {
        _context = context;
        _mapper = mapper;
        _logger = logger;
        _idGenerator = idGenerator;
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

    public async Task<OrderResponseDto> CreateAsync(OrderCreateDto dto)
    {
        using var transaction = await _context.Database.BeginTransactionAsync();
        
        try
        {
            // Generate order number using Snowflake ID
            var orderNumber = $"ORD-{_idGenerator.Generate()}";
            
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

            _logger.LogInformation("Created order {OrderNumber} for {CustomerEmail}", orderNumber, dto.CustomerEmail);

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
