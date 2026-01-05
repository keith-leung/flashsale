using System.Text.Json;
using FlashSale.Api.Models;
using StackExchange.Redis;

namespace FlashSale.Api.Services;

public class RedisCacheService
{
    private readonly IConnectionMultiplexer _redis;
    private readonly IDatabase _db;
    private readonly ILogger<RedisCacheService> _logger;
    private const string SkuKeyPrefix = "sku:";
    private const string SkuMetaPrefix = "sku:";
    private const string CampaignLimitPrefix = "fs:";
    private const string CampaignMetaPrefix = "fs:";
    private const string InventoryPrefix = "inv:";
    private const string OrderQueue = "order_queue";
    private readonly TimeSpan _skuTtl = TimeSpan.FromMinutes(10);

    public RedisCacheService(IConnectionMultiplexer redis, ILogger<RedisCacheService> logger)
    {
        _redis = redis;
        _db = redis.GetDatabase();
        _logger = logger;
    }

    public async Task<Dictionary<Guid, SkuCacheData>> GetMultiSkuAsync(IEnumerable<Guid> skuIds)
    {
        var ids = skuIds.ToList();
        if (!ids.Any()) return new Dictionary<Guid, SkuCacheData>();

        var keys = ids.Select(id => (RedisKey)(SkuKeyPrefix + id)).ToArray();
        var results = await _db.StringGetAsync(keys);

        var cachedSkus = new Dictionary<Guid, SkuCacheData>();

        for (int i = 0; i < ids.Count; i++)
        {
            if (results[i].HasValue)
            {
                try
                {
                    var data = JsonSerializer.Deserialize<SkuCacheData>(results[i]!);
                    if (data != null)
                    {
                        cachedSkus[ids[i]] = data;
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Error deserializing SKU cache data for ID: {SkuId}", ids[i]);
                }
            }
        }

        return cachedSkus;
    }

    public async Task SetMultiSkuAsync(Dictionary<Guid, SkuCacheData> dataMap)
    {
        if (!dataMap.Any()) return;

        var batch = _db.CreateBatch();
        var tasks = new List<Task>();

        foreach (var kvp in dataMap)
        {
            var key = SkuKeyPrefix + kvp.Key;
            var json = JsonSerializer.Serialize(kvp.Value);
            tasks.Add(batch.StringSetAsync(key, json, _skuTtl));
        }

        batch.Execute();
        await Task.WhenAll(tasks);
    }

    public async Task InvalidateSkuAsync(Guid skuId)
    {
        await _db.KeyDeleteAsync(SkuKeyPrefix + skuId);
    }

    // ============ Flash Sale Campaign Methods ============

    /// <summary>
    /// Get campaign limit remaining (atomic read)
    /// </summary>
    public async Task<long?> GetCampaignLimitAsync(Guid campaignId)
    {
        var key = $"{CampaignLimitPrefix}{campaignId}:limit";
        var value = await _db.StringGetAsync(key);
        return value.HasValue ? (long?)long.Parse(value!) : null;
    }

    /// <summary>
    /// Get campaign metadata
    /// </summary>
    public async Task<Dictionary<string, string>?> GetCampaignMetaAsync(Guid campaignId)
    {
        var key = $"{CampaignMetaPrefix}{campaignId}:meta";
        var entries = await _db.HashGetAllAsync(key);

        if (entries == null || entries.Length == 0)
            return null;

        var result = new Dictionary<string, string>();
        foreach (var entry in entries)
        {
            result[entry.Name.ToString()] = entry.Value.ToString();
        }
        return result;
    }

    /// <summary>
    /// Set campaign metadata
    /// </summary>
    public async Task SetCampaignMetaAsync(Guid campaignId, Dictionary<string, string> meta)
    {
        var key = $"{CampaignMetaPrefix}{campaignId}:meta";
        var hashEntries = meta.Select(kvp => new HashEntry(kvp.Key, kvp.Value)).ToArray();
        await _db.HashSetAsync(key, hashEntries);
    }

    /// <summary>
    /// Set campaign limit
    /// </summary>
    public async Task SetCampaignLimitAsync(Guid campaignId, long limit)
    {
        var key = $"{CampaignLimitPrefix}{campaignId}:limit";
        await _db.StringSetAsync(key, limit);
    }

    /// <summary>
    /// Atomically reserve inventory from campaign limit (DECR)
    /// Returns new value after decrement
    /// </summary>
    public async Task<long> ReserveCampaignInventoryAsync(Guid campaignId, int quantity)
    {
        var key = $"{CampaignLimitPrefix}{campaignId}:limit";
        return await _db.StringDecrementAsync(key, quantity);
    }

    /// <summary>
    /// Release campaign inventory (rollback)
    /// </summary>
    public async Task<long> ReleaseCampaignInventoryAsync(Guid campaignId, int quantity)
    {
        var key = $"{CampaignLimitPrefix}{campaignId}:limit";
        return await _db.StringIncrementAsync(key, quantity);
    }

    /// <summary>
    /// Get SKU inventory level
    /// </summary>
    public async Task<long?> GetSkuInventoryAsync(Guid skuId)
    {
        var key = $"{InventoryPrefix}{skuId}";
        var value = await _db.StringGetAsync(key);
        return value.HasValue ? (long?)long.Parse(value!) : null;
    }

    /// <summary>
    /// Set SKU inventory level
    /// </summary>
    public async Task SetSkuInventoryAsync(Guid skuId, long quantity)
    {
        var key = $"{InventoryPrefix}{skuId}";
        await _db.StringSetAsync(key, quantity);
    }

    /// <summary>
    /// Atomically reserve SKU inventory (DECR)
    /// </summary>
    public async Task<long> ReserveSkuInventoryAsync(Guid skuId, int quantity)
    {
        var key = $"{InventoryPrefix}{skuId}";
        return await _db.StringDecrementAsync(key, quantity);
    }

    /// <summary>
    /// Release SKU inventory (rollback)
    /// </summary>
    public async Task<long> ReleaseSkuInventoryAsync(Guid skuId, int quantity)
    {
        var key = $"{InventoryPrefix}{skuId}";
        return await _db.StringIncrementAsync(key, quantity);
    }

    /// <summary>
    /// Get SKU metadata from Redis hash
    /// </summary>
    public async Task<Dictionary<string, string>?> GetSkuMetaAsync(Guid skuId)
    {
        var key = $"{SkuMetaPrefix}{skuId}:meta";
        var entries = await _db.HashGetAllAsync(key);

        if (entries == null || entries.Length == 0)
            return null;

        var result = new Dictionary<string, string>();
        foreach (var entry in entries)
        {
            result[entry.Name.ToString()] = entry.Value.ToString();
        }
        return result;
    }

    /// <summary>
    /// Set SKU metadata
    /// </summary>
    public async Task SetSkuMetaAsync(Guid skuId, Dictionary<string, string> meta)
    {
        var key = $"{SkuMetaPrefix}{skuId}:meta";
        var hashEntries = meta.Select(kvp => new HashEntry(kvp.Key, kvp.Value)).ToArray();
        await _db.HashSetAsync(key, hashEntries);
    }

    /// <summary>
    /// Queue order for async batch processing
    /// </summary>
    public async Task QueueOrderAsync(Dictionary<string, object> orderData)
    {
        try
        {
            var json = JsonSerializer.Serialize(orderData);
            var streamPair = new NameValueEntry("order_data", json);
            await _db.StreamAddAsync(OrderQueue, new[] { streamPair });
            _logger.LogDebug("Order queued to Redis stream: {Queue}", OrderQueue);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to queue order to Redis stream");
            throw new InvalidOperationException("Failed to queue order", ex);
        }
    }
}

public class SkuCacheData
{
    public Guid Id { get; set; }
    public string SkuCode { get; set; } = string.Empty;
    public decimal Price { get; set; }
    public int Quantity { get; set; }
    public int ReservedQuantity { get; set; }
    public bool AllowNegativeStock { get; set; }
    public string SpuName { get; set; } = string.Empty;
    public bool TrackInventory { get; set; }
    public bool IsActive { get; set; }

    public static SkuCacheData FromEntity(Sku sku)
    {
        return new SkuCacheData
        {
            Id = sku.Id,
            SkuCode = sku.SkuCode,
            Price = sku.Price,
            Quantity = sku.Inventory?.Quantity ?? 0,
            ReservedQuantity = sku.Inventory?.ReservedQuantity ?? 0,
            AllowNegativeStock = sku.Inventory?.AllowNegativeStock ?? false,
            SpuName = sku.Spu?.Name ?? (sku.Name ?? "Product"),
            TrackInventory = sku.TrackInventory,
            IsActive = sku.IsActive
        };
    }
}
