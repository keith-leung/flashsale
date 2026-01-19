using FlashSale.Data;
using FlashSale.DTOs;
using FlashSale.Models;
using Microsoft.EntityFrameworkCore;
using System.Security.Cryptography;

namespace FlashSale.Services;

public interface IOrderService
{
    Task<OrderResponse> CreateOrderAsync(OrderRequest request);
    Task<Order?> GetOrderByIdAsync(Guid orderId);
}

public class OrderService : IOrderService
{
    private readonly FlashSaleDbContext _dbContext;
    private readonly ITokenService _tokenService;
    private readonly ILogger<OrderService> _logger;

    public OrderService(FlashSaleDbContext dbContext, ITokenService tokenService, ILogger<OrderService> logger)
    {
        _dbContext = dbContext;
        _tokenService = tokenService;
        _logger = logger;
    }

    public async Task<OrderResponse> CreateOrderAsync(OrderRequest request)
    {
        // Validate request
        if (request.LineItems == null || !request.LineItems.Any())
        {
            throw new ArgumentException("Order must contain at least one line item");
        }

        var firstSku = await _dbContext.Skus
            .Include(s => s.Spu)
            .FirstOrDefaultAsync(s => s.Id == request.LineItems[0].SkuId);

        if (firstSku == null)
        {
            throw new ArgumentException($"SKU {request.LineItems[0].SkuId} not found");
        }

        var campaign = await _tokenService.GetActiveCampaignForSpuAsync(firstSku.SpuId);
        Guid? campaignId = campaign?.Id;

        // If campaign exists, use Variant Z path (token pre-allocation)
        if (campaign != null)
        {
            foreach (var lineItem in request.LineItems)
            {
                var tokenResult = await _tokenService.AcquireTokenAsync(
                    campaignId!.Value, 
                    lineItem.SkuId, 
                    lineItem.Quantity
                );

                if (tokenResult.ContainsKey("err"))
                {
                    throw new InvalidOperationException(tokenResult["err"].ToString());
                }
            }
        }
        else
        {
            // Variant Y path: direct database transaction
            // (For simplicity, we'll just skip token acquisition)
            _logger.LogInformation("No active campaign found, using standard order path");
        }

        // Synchronously persist order to database
        var order = await PersistOrderSynchronouslyAsync(request, campaignId, firstSku);

        return new OrderResponse
        {
            OrderId = order.Id,
            OrderNumber = order.OrderNumber,
            Status = order.Status,
            TotalAmount = order.TotalAmount,
            CustomerEmail = order.CustomerEmail
        };
    }

    private async Task<Order> PersistOrderSynchronouslyAsync(OrderRequest request, Guid? campaignId, Sku firstSku)
    {
        // Generate unique order number
        var orderNumber = GenerateOrderNumber();
        var orderId = Guid.NewGuid();

        decimal totalAmount = 0;
        var lineItems = new List<OrderLineItem>();

        // Load all SKUs with inventory
        var skuIds = request.LineItems.Select(li => li.SkuId).ToList();
        var skus = await _dbContext.Skus
            .Include(s => s.Inventory)
            .Where(s => skuIds.Contains(s.Id))
            .ToDictionaryAsync(s => s.Id, s => s);

        // Create line items and calculate total
        foreach (var lineItemRequest in request.LineItems)
        {
            if (!skus.TryGetValue(lineItemRequest.SkuId, out var sku))
            {
                throw new ArgumentException($"SKU {lineItemRequest.SkuId} not found");
            }

            if (sku.Inventory == null || sku.Inventory.Quantity < lineItemRequest.Quantity)
            {
                throw new InvalidOperationException($"Insufficient stock for SKU {sku.Id}");
            }

            var unitPrice = sku.Inventory.Quantity > 0 ? 10.00m : 0.00m; // Simplified pricing
            var lineItemTotal = unitPrice * lineItemRequest.Quantity;
            totalAmount += lineItemTotal;

            lineItems.Add(new OrderLineItem
            {
                Id = Guid.NewGuid(),
                OrderId = orderId,
                SkuId = lineItemRequest.SkuId,
                Quantity = lineItemRequest.Quantity,
                UnitPrice = unitPrice,
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow
            });
        }

        // Synchronous database transaction
        using var transaction = await _dbContext.Database.BeginTransactionAsync();
        try
        {
            // Create order
            var order = new Order
            {
                Id = orderId,
                OrderNumber = orderNumber,
                CustomerName = request.CustomerName,
                CustomerEmail = request.CustomerEmail,
                Status = "pending",
                TotalAmount = totalAmount,
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow,
                LineItems = lineItems
            };

            _dbContext.Orders.Add(order);

            // Create payment
            var payment = new Payment
            {
                Id = Guid.NewGuid(),
                OrderId = orderId,
                Amount = totalAmount,
                Status = "pending",
                PaymentMethod = "test",
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow
            };

            _dbContext.Payments.Add(payment);

            // Update inventory
            foreach (var lineItem in lineItems)
            {
                var sku = skus[lineItem.SkuId];
                if (sku.Inventory != null)
                {
                    sku.Inventory.Quantity -= lineItem.Quantity;
                    sku.Inventory.UpdatedAt = DateTime.UtcNow;
                }

                // Update campaign sold quantity if applicable
                if (campaignId.HasValue)
                {
                    var campaign = await _dbContext.FlashSaleCampaigns.FindAsync(campaignId.Value);
                    if (campaign != null)
                    {
                        campaign.SoldQuantity += lineItem.Quantity;
                        campaign.UpdatedAt = DateTime.UtcNow;
                    }
                }
            }

            // Commit transaction
            await _dbContext.SaveChangesAsync();
            await transaction.CommitAsync();

            _logger.LogInformation("Order {OrderNumber} persisted successfully", orderNumber);

            return order;
        }
        catch (Exception ex)
        {
            await transaction.RollbackAsync();
            _logger.LogError(ex, "Failed to persist order {OrderNumber}", orderNumber);
            throw;
        }
    }

    private string GenerateOrderNumber()
    {
        var timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        var randomBytes = new byte[4];
        RandomNumberGenerator.Fill(randomBytes);
        var randomPart = BitConverter.ToUInt32(randomBytes, 0);
        return $"ORD-{timestamp}-{randomPart}";
    }

    public async Task<Order?> GetOrderByIdAsync(Guid orderId)
    {
        return await _dbContext.Orders
            .Include(o => o.LineItems)
            .ThenInclude(li => li.Sku)
            .Include(o => o.Payments)
            .FirstOrDefaultAsync(o => o.Id == orderId);
    }
}