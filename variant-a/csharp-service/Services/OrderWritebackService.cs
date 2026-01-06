using System.Text.Json;
using FlashSale.Api.Data;
using FlashSale.Api.Models;
using Microsoft.EntityFrameworkCore;
using StackExchange.Redis;

namespace FlashSale.Api.Services;



/// <summary>
/// Background service to process queued orders from Redis Stream and write to database
/// </summary>
public class OrderWritebackService : BackgroundService
{
    private readonly IServiceProvider _serviceProvider;
    private readonly ILogger<OrderWritebackService> _logger;
    private readonly IConnectionMultiplexer _redis;
    private readonly TimeSpan _pollInterval = TimeSpan.FromSeconds(5); // Poll every 5 seconds
    private const string OrderQueueStream = "order_queue";
    private const string ConsumerGroup = "csharp-writeback";
    private const string ConsumerName = "csharp-worker";
    private const int BatchSize = 100;

    public OrderWritebackService(
        IServiceProvider serviceProvider,
        ILogger<OrderWritebackService> logger,
        IConnectionMultiplexer redis)
    {
        _serviceProvider = serviceProvider;
        _logger = logger;
        _redis = redis;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Order Writeback Service started");

        var db = _redis.GetDatabase();

        // Create consumer group if it doesn't exist
        try
        {
            await db.StreamCreateConsumerGroupAsync(OrderQueueStream, ConsumerGroup, "0-0", true);
            _logger.LogInformation("Created consumer group '{ConsumerGroup}' for stream '{Stream}'", ConsumerGroup, OrderQueueStream);
        }
        catch (RedisServerException ex) when (ex.Message.Contains("BUSYGROUP"))
        {
            _logger.LogDebug("Consumer group '{ConsumerGroup}' already exists", ConsumerGroup);
        }

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                // Read pending messages first (in case of previous failures)
                await ProcessPendingMessages(db, stoppingToken);

                // Read new messages
                await ProcessNewMessages(db, stoppingToken);

                await Task.Delay(_pollInterval, stoppingToken);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error occurred in Order Writeback Service");
                await Task.Delay(TimeSpan.FromSeconds(10), stoppingToken);
            }
        }

        _logger.LogInformation("Order Writeback Service stopped");
    }

    private async Task ProcessNewMessages(IDatabase db, CancellationToken stoppingToken)
    {
        var messages = await db.StreamReadGroupAsync(
            OrderQueueStream,
            ConsumerGroup,
            ConsumerName,
            ">", // Read only new messages
            BatchSize);

        if (messages.Length > 0)
        {
            _logger.LogInformation("Processing {Count} new orders from queue", messages.Length);
            await ProcessMessages(db, messages, stoppingToken);
        }
    }

    private async Task ProcessPendingMessages(IDatabase db, CancellationToken stoppingToken)
    {
        var pending = await db.StreamPendingMessagesAsync(
            OrderQueueStream,
            ConsumerGroup,
            BatchSize,
            ConsumerName);

        if (pending.Length > 0)
        {
            _logger.LogWarning("Found {Count} pending messages, reprocessing...", pending.Length);

            var pendingIds = pending.Select(p => p.MessageId).ToArray();
            var messages = await db.StreamClaimAsync(
                OrderQueueStream,
                ConsumerGroup,
                ConsumerName,
                minIdleTimeInMs: 60000, // Claim messages idle for 1 minute
                messageIds: pendingIds);

            await ProcessMessages(db, messages, stoppingToken);
        }
    }

    private async Task ProcessMessages(IDatabase db, StreamEntry[] messages, CancellationToken stoppingToken)
    {
        using var scope = _serviceProvider.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<FlashSaleDbContext>();

        foreach (var message in messages)
        {
            if (stoppingToken.IsCancellationRequested)
                break;

            try
            {
                var orderData = message.Values.FirstOrDefault(v => v.Name == "order_data").Value;
                if (orderData.IsNullOrEmpty)
                {
                    _logger.LogWarning("Empty order_data in message {MessageId}", message.Id);
                    await db.StreamAcknowledgeAsync(OrderQueueStream, ConsumerGroup, message.Id);
                    continue;
                }

                var orderDict = JsonSerializer.Deserialize<Dictionary<string, object>>(orderData!);
                if (orderDict == null)
                {
                    _logger.LogWarning("Failed to deserialize order_data in message {MessageId}", message.Id);
                    await db.StreamAcknowledgeAsync(OrderQueueStream, ConsumerGroup, message.Id);
                    continue;
                }

                await WriteOrderToDatabase(context, orderDict);

                // Acknowledge message after successful processing
                await db.StreamAcknowledgeAsync(OrderQueueStream, ConsumerGroup, message.Id);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing message {MessageId}", message.Id);
                // Don't acknowledge - will be reprocessed later
            }
        }

        // Save all changes in a single transaction
        try
        {
            await context.SaveChangesAsync(stoppingToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error saving batch of orders to database");
        }
    }

    private async Task WriteOrderToDatabase(FlashSaleDbContext context, Dictionary<string, object> orderData)
    {
        var orderNumber = orderData.GetValueOrDefault("order_number")?.ToString();
        if (string.IsNullOrEmpty(orderNumber))
        {
            _logger.LogWarning("Missing order_number in order data");
            return;
        }

        // Check if order already exists (idempotency)
        var exists = await context.Orders.AnyAsync(o => o.OrderNumber == orderNumber);
        if (exists)
        {
            _logger.LogDebug("Order {OrderNumber} already exists, skipping", orderNumber);
            return;
        }

        var customerEmail = orderData.GetValueOrDefault("customer_email")?.ToString() ?? "";
        var customerName = orderData.GetValueOrDefault("customer_name")?.ToString() ?? "";
        var flashSaleIdStr = orderData.GetValueOrDefault("flash_sale_id")?.ToString();

        Guid? flashSaleId = null;
        if (flashSaleIdStr != null && Guid.TryParse(flashSaleIdStr, out var parsedId))
        {
            flashSaleId = parsedId;
        }

        // Parse line items
        var lineItemsJson = orderData.GetValueOrDefault("line_items");
        var lineItemsList = new List<Dictionary<string, object>>();

        if (lineItemsJson != null)
        {
            if (lineItemsJson is JsonElement jsonElement)
            {
                lineItemsList = JsonSerializer.Deserialize<List<Dictionary<string, object>>>(jsonElement.GetRawText())
                    ?? new List<Dictionary<string, object>>();
            }
            else if (lineItemsJson is string jsonString)
            {
                lineItemsList = JsonSerializer.Deserialize<List<Dictionary<string, object>>>(jsonString)
                    ?? new List<Dictionary<string, object>>();
            }
        }

        if (lineItemsList.Count == 0)
        {
            _logger.LogWarning("No line items in order {OrderNumber}", orderNumber);
            return;
        }

        // Create order entity
        var order = new Models.Order
        {
            OrderNumber = orderNumber,
            CustomerEmail = customerEmail,
            CustomerName = customerName,
            FlashSaleCampaignId = flashSaleId,
            Status = OrderStatus.Pending,
            Currency = "USD"
        };

        decimal subtotal = 0;

        foreach (var itemData in lineItemsList)
        {
            var skuIdStr = itemData.GetValueOrDefault("sku_id")?.ToString();
            if (skuIdStr == null || !Guid.TryParse(skuIdStr, out var skuId))
            {
                _logger.LogWarning("Invalid sku_id in order {OrderNumber}", orderNumber);
                continue;
            }

            var quantity = Convert.ToInt32(itemData.GetValueOrDefault("quantity"));
            var unitPriceStr = itemData.GetValueOrDefault("unit_price")?.ToString() ?? "0";
            var unitPrice = decimal.Parse(unitPriceStr);

            // Get SKU info
            var sku = await context.Skus
                .Include(s => s.Spu)
                .FirstOrDefaultAsync(s => s.Id == skuId);

            if (sku == null)
            {
                _logger.LogWarning("SKU {SkuId} not found for order {OrderNumber}", skuId, orderNumber);
                continue;
            }

            // If unit price is 0, try to get from flash sale or SKU
            if (unitPrice == 0 && flashSaleId.HasValue)
            {
                var flashSale = await context.FlashSaleCampaigns
                    .FirstOrDefaultAsync(f => f.Id == flashSaleId.Value);
                unitPrice = flashSale?.FlashPrice ?? sku.Price;
            }
            else if (unitPrice == 0)
            {
                unitPrice = sku.Price;
            }

            var totalPrice = unitPrice * quantity;
            subtotal += totalPrice;

            var lineItem = new OrderLineItem
            {
                OrderId = order.Id,
                SkuId = skuId,
                Quantity = quantity,
                UnitPrice = unitPrice,
                TotalPrice = totalPrice,
                ProductName = sku.Spu?.Name ?? sku.Name ?? "Product",
                SkuCode = sku.SkuCode
            };

            order.LineItems.Add(lineItem);
        }

        order.Subtotal = subtotal;
        order.TaxAmount = 0;
        order.ShippingAmount = 0;
        order.TotalAmount = subtotal;

        context.Orders.Add(order);

        _logger.LogInformation("Writing order {OrderNumber} to database (Subtotal: {Subtotal}, Items: {ItemCount})",
            orderNumber, subtotal, order.LineItems.Count);
    }
}
