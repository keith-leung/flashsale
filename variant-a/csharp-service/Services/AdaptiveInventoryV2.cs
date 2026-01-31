using StackExchange.Redis;
using System.Collections.Concurrent;

namespace FlashSale.Api.Services;

/// <summary>
/// Adaptive Inventory V2 - Producer-Consumer Pattern with Async Refills
///
/// Corrected implementation for Variant A (matches Java/Python exactly):
/// - Each allocation unit starts with allocated_quantity items in RAM (e.g., 500)
/// - When hitting low water mark (e.g., 30% = 150 items), trigger async refill
/// - Async refill pulls refill_batch_size items (e.g., 50) from Redis campaign pool
/// - Refills cascade: 500→150→45→13... (each refill hits new 30% threshold)
/// - Three-tier fallback: Local RAM → Redis campaign pool → Ordinary stock
/// </summary>
public class AdaptiveInventoryV2
{
    private readonly ILogger<AdaptiveInventoryV2> _logger;

    // Allocation unit configuration
    private readonly long _allocationId;
    private readonly Guid _campaignId;
    private readonly Guid _skuId;
    private readonly int _allocatedQuantity;      // Initial quantity (e.g., 500)
    private readonly int _refillBatchSize;         // Refill amount (e.g., 50)
    private readonly decimal _lowWaterMarkPct;     // e.g., 0.30 (30%)

    // Redis client
    private readonly IDatabase _redis;
    private readonly string _campaignPoolKey;  // fs:{campaignId}:redis_pool:sku:{skuId}

    // Local stock management (Producer-Consumer)
    private int _localStock;
    private int _currentLowWaterMark;
    private readonly SemaphoreSlim _stockLock = new(1, 1);

    // Refill management (single-flight pattern)
    private int _refillInProgress = 0;

    // Metrics
    private long _totalRequests = 0;
    private long _ramHits = 0;
    private long _redisRefills = 0;
    private long _campaignPoolHits = 0;
    private long _ordinaryStockFallbacks = 0;

    public AdaptiveInventoryV2(
        long allocationId,
        Guid campaignId,
        Guid skuId,
        int allocatedQuantity,
        int refillBatchSize,
        decimal lowWaterMarkPct,
        IDatabase redis,
        ILogger<AdaptiveInventoryV2> logger)
    {
        _allocationId = allocationId;
        _campaignId = campaignId;
        _skuId = skuId;
        _allocatedQuantity = allocatedQuantity;
        _refillBatchSize = refillBatchSize;
        _lowWaterMarkPct = lowWaterMarkPct;
        _redis = redis;
        _logger = logger;

        // Initialize local stock with allocated quantity
        _localStock = allocatedQuantity;

        // Calculate initial low water mark (30% of allocated quantity)
        _currentLowWaterMark = (int)(allocatedQuantity * (double)lowWaterMarkPct);

        // Redis key for campaign pool (Partitioned SKU pool)
        _campaignPoolKey = $"fs:{campaignId}:redis_pool:sku:{skuId}";

        _logger.LogInformation(
            "[Allocation {AllocationId}] Initialized: {AllocatedQty} items in RAM, low_water_mark={LowWaterMark}, refill_batch={RefillBatch}, source={PoolKey}",
            allocationId, allocatedQuantity, _currentLowWaterMark, refillBatchSize, _campaignPoolKey
        );
    }

    /// <summary>
    /// Reserve one item using producer-consumer pattern
    /// Returns: (success, priceType, price)
    /// </summary>
    public async Task<(bool Success, string PriceType, decimal Price)> ReserveItemAsync()
    {
        Interlocked.Increment(ref _totalRequests);

        // CONSUMER: Try local RAM first (fast path - pure memory)
        int current = Volatile.Read(ref _localStock);
        if (current > 0)
        {
            await _stockLock.WaitAsync();
            try
            {
                if (_localStock > 0)
                {
                    _localStock--;
                    Interlocked.Increment(ref _ramHits);

                    int newStock = _localStock;

                    // PRODUCER: Check if we hit low water mark → trigger async refill
                    if (newStock == _currentLowWaterMark && Interlocked.CompareExchange(ref _refillInProgress, 1, 0) == 0)
                    {
                        // Start async refill (fire-and-forget)
                        _ = Task.Run(async () => await DoRefillAsync());
                    }

                    return (true, "campaign", 9.99m);  // Success from RAM
                }
            }
            finally
            {
                _stockLock.Release();
            }
        }

        // RAM depleted → fall back to campaign pool
        return await HandleDepletedAsync();
    }

    /// <summary>
    /// Handle case when local RAM is depleted
    /// Fallback: Redis campaign pool → Ordinary stock
    /// </summary>
    private async Task<(bool Success, string PriceType, decimal Price)> HandleDepletedAsync()
    {
        // Try campaign pool directly (bypassing local cache)
        long remaining = await _redis.StringDecrementAsync(_campaignPoolKey);
        if (remaining >= 0)
        {
            Interlocked.Increment(ref _campaignPoolHits);
            _logger.LogDebug(
                "[Allocation {AllocationId}] Campaign pool hit: {Remaining} remaining",
                _allocationId, remaining
            );
            return (true, "campaign", 9.99m);
        }
        else
        {
            // Campaign sold out → restore Redis counter and try ordinary stock
            await _redis.StringIncrementAsync(_campaignPoolKey);

            // TODO: Check ordinary stock from database (inventory table)
            // For now, return sold out
            Interlocked.Increment(ref _ordinaryStockFallbacks);
            return (false, "sold_out", 0m);
        }
    }

    /// <summary>
    /// PRODUCER: Async refill from Redis campaign pool
    /// Runs in background, doesn't block request thread
    /// </summary>
    private async Task DoRefillAsync()
    {
        try
        {
            var startTime = DateTime.UtcNow;

            // Try to pull refill_batch_size items from campaign pool
            long newRemaining = await _redis.StringDecrementAsync(_campaignPoolKey, _refillBatchSize);

            if (newRemaining >= 0)
            {
                // Success! Refill local stock
                await _stockLock.WaitAsync();
                try
                {
                    _localStock += _refillBatchSize;
                    Interlocked.Increment(ref _redisRefills);

                    // Calculate new low water mark (cascading: 500→150→45→13...)
                    int newLowWaterMark = (int)(_localStock * (double)_lowWaterMarkPct);
                    _currentLowWaterMark = newLowWaterMark;

                    var duration = (DateTime.UtcNow - startTime).TotalMilliseconds;

                    _logger.LogDebug(
                        "[Allocation {AllocationId}] Refill SUCCESS: +{RefillAmount} items, new_stock={NewStock}, " +
                        "new_low_water_mark={NewLowWaterMark}, campaign_pool_remaining={CampaignRemaining}, latency={Latency}ms",
                        _allocationId, _refillBatchSize, _localStock, newLowWaterMark, newRemaining, duration
                    );
                }
                finally
                {
                    _stockLock.Release();
                }
            }
            else
            {
                // Campaign pool depleted → restore what we tried to take
                await _redis.StringIncrementAsync(_campaignPoolKey, _refillBatchSize);

                _logger.LogInformation(
                    "[Allocation {AllocationId}] Refill FAILED: Campaign pool depleted, remaining={CampaignRemaining}",
                    _allocationId, newRemaining
                );
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "[Allocation {AllocationId}] Refill ERROR: {ErrorMessage}",
                _allocationId, ex.Message
            );
        }
        finally
        {
            // Release refill lock
            Interlocked.Exchange(ref _refillInProgress, 0);
        }
    }

    /// <summary>
    /// Get current metrics for monitoring
    /// </summary>
    public AdaptiveInventoryMetrics GetMetrics()
    {
        return new AdaptiveInventoryMetrics
        {
            AllocationId = _allocationId,
            TotalRequests = _totalRequests,
            RamHits = _ramHits,
            RedisRefills = _redisRefills,
            CampaignPoolHits = _campaignPoolHits,
            OrdinaryStockFallbacks = _ordinaryStockFallbacks,
            CurrentLocalStock = _localStock,
            CurrentLowWaterMark = _currentLowWaterMark
        };
    }
}

/// <summary>
/// Metrics data class for adaptive inventory
/// </summary>
public class AdaptiveInventoryMetrics
{
    public long AllocationId { get; set; }
    public long TotalRequests { get; set; }
    public long RamHits { get; set; }
    public long RedisRefills { get; set; }
    public long CampaignPoolHits { get; set; }
    public long OrdinaryStockFallbacks { get; set; }
    public int CurrentLocalStock { get; set; }
    public int CurrentLowWaterMark { get; set; }
}
