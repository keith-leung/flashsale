using StackExchange.Redis;
using System.Threading;

namespace FlashSale.Api.Services;

/// <summary>
/// Adaptive Inventory Service for Flash Sale Variant A
///
/// Uses a 2-tier adaptive strategy:
/// - BATCH MODE: Local cache with SemaphoreSlim (500 items)
/// - DIRECT MODE: Direct Redis calls when stock &lt; LOW_WATER_MARK
///
/// Network I/O Reduction: 99.6%+ (500 requests = 1 Redis call in batch mode)
/// </summary>
public class AdaptiveInventoryService
{
    private static readonly ILogger<AdaptiveInventoryService> _staticLogger =
        LoggerFactory.Create(builder => builder.AddConsole()).CreateLogger<AdaptiveInventoryService>();

    // Configuration constants
    public const int BATCH_SIZE = 500;
    public const int LOW_WATER_MARK = 2000;

    private readonly string _campaignId;
    private readonly string _skuId;
    private readonly IDatabase _db;
    private readonly string _luaScriptSha;

    // Redis key for this SKU's inventory
    private readonly string _inventoryKey;

    // L1 Cache (Local Memory)
    private long _localStock = 0;

    // Mode control
    private bool _directMode = false;
    private bool _modeSwitched = false;

    // Single-flight refill protection
    private readonly SemaphoreSlim _stockLock = new(1, 1);
    private readonly SemaphoreSlim _refillLock = new(1, 1);

    // Metrics
    private long _batchModeRequests = 0;
    private long _directModeRequests = 0;
    private long _totalRedisCalls = 0;

    public AdaptiveInventoryService(
        string campaignId,
        string skuId,
        IDatabase db,
        string luaScriptSha)
    {
        _campaignId = campaignId;
        _skuId = skuId;
        _db = db;
        _luaScriptSha = luaScriptSha;
        _inventoryKey = $"fs:{campaignId}:redis_pool:sku:{skuId}";
    }

    /// <summary>
    /// Attempt to reserve one item from inventory
    ///
    /// Hot Path Flow:
    /// 1. Try local cache (pure memory, no network)
    /// 2. If cache empty, spin-wait for refill (critical for 100K+ req/s)
    /// 3. If directMode, bypass cache and hit Redis
    /// </summary>
    /// <returns>True if reservation successful, false if sold out</returns>
    public async Task<bool> ReserveItemAsync()
    {
        // Fast path: Try local cache first (BATCH MODE)
        if (!_directMode)
        {
            // Try to get stock without lock first (optimistic read)
            if (_localStock > 0)
            {
                await _stockLock.WaitAsync();
                try
                {
                    if (_localStock > 0)
                    {
                        _localStock--;
                        Interlocked.Increment(ref _batchModeRequests);
                        return true;  // ← Network I/O saved here! Pure RAM operation
                    }
                }
                finally
                {
                    _stockLock.Release();
                }
            }

            // Stock is 0 - spin wait for refill (critical for 100K+ req/s)
            // A refill might be 5-10ms away, avoid false "sold out"
            bool stockAvailable = SpinWait.SpinUntil(() => _localStock > 0, millisecondsTimeout: 10);

            if (stockAvailable)
            {
                await _stockLock.WaitAsync();
                try
                {
                    if (_localStock > 0)
                    {
                        _localStock--;
                        Interlocked.Increment(ref _batchModeRequests);
                        return true;  // Caught the refill!
                    }
                }
                finally
                {
                    _stockLock.Release();
                }
            }
        }

        // Slow path: Refill or direct Redis
        return await RefillOrDirectAsync();
    }

    /// <summary>
    /// Refill local cache from Redis or switch to direct mode
    /// Uses single-flight pattern to prevent stampede
    /// </summary>
    private async Task<bool> RefillOrDirectAsync()
    {
        await _refillLock.WaitAsync();
        try
        {
            // Double-check: another thread might have refilled
            if (!_directMode)
            {
                await _stockLock.WaitAsync();
                try
                {
                    if (_localStock > 0)
                    {
                        _localStock--;
                        Interlocked.Increment(ref _batchModeRequests);
                        return true;
                    }
                }
                finally
                {
                    _stockLock.Release();
                }
            }

            if (_directMode)
            {
                // Direct mode: hit Redis for every request
                return await TryDirectRedisAsync();
            }
            else
            {
                // Batch mode: try to refill from Redis
                return await TryRefillBatchAsync();
            }
        }
        finally
        {
            _refillLock.Release();
        }
    }

    /// <summary>
    /// Try to refill local cache from Redis using Lua script
    /// </summary>
    private async Task<bool> TryRefillBatchAsync()
    {
        Interlocked.Increment(ref _totalRedisCalls);

        // Execute Lua script
        // KEYS[1] = inventory key
        // ARGV[1] = batch size
        // ARGV[2] = low water mark
        var result = await _db.ScriptEvaluateAsync(
            _luaScriptSha,
            new RedisKey[] { _inventoryKey },
            new RedisValue[] { BATCH_SIZE, LOW_WATER_MARK }
        );

        if (result.IsNull)
        {
            _staticLogger.LogError("Lua script returned null for SKU: {SkuId}", _skuId);
            return false;
        }

        long granted = (long)result;

        if (granted == -1)
        {
            // Sold out
            _staticLogger.LogDebug("SKU {SkuId} sold out", _skuId);
            return false;
        }
        else if (granted == -2)
        {
            // Switch to direct mode
            if (!_modeSwitched)
            {
                _modeSwitched = true;
                _staticLogger.LogInformation(
                    "[MODE SWITCH] SKU {SkuId}: Stock below {LowWaterMark} - switching to DIRECT mode to prevent fragmentation",
                    _skuId, LOW_WATER_MARK);
            }
            _directMode = true;
            return await TryDirectRedisAsync();
        }
        else
        {
            // Granted batch
            await _stockLock.WaitAsync();
            try
            {
                _localStock = granted;
                if (_localStock > 0)
                {
                    _localStock--;
                    Interlocked.Increment(ref _batchModeRequests);
                    return true;
                }
            }
            finally
            {
                _stockLock.Release();
            }
            return false;
        }
    }

    /// <summary>
    /// Direct Redis mode - hit Redis for every request
    /// Used when stock &lt; LOW_WATER_MARK to prevent fragmentation
    /// </summary>
    private async Task<bool> TryDirectRedisAsync()
    {
        Interlocked.Increment(ref _totalRedisCalls);
        Interlocked.Increment(ref _directModeRequests);

        // Atomic decrement
        long stock = await _db.StringDecrementAsync(_inventoryKey);
        if (stock >= 0)
        {
            return true;
        }
        else
        {
            // Restore if went negative
            await _db.StringIncrementAsync(_inventoryKey);
            return false;
        }
    }

    /// <summary>
    /// Get current metrics
    /// </summary>
    public InventoryMetrics GetMetrics()
    {
        return new InventoryMetrics
        {
            BatchModeRequests = _batchModeRequests,
            DirectModeRequests = _directModeRequests,
            TotalRedisCalls = _totalRedisCalls,
            ModeSwitched = _modeSwitched
        };
    }

    /// <summary>
    /// Get current operation mode
    /// </summary>
    public string CurrentMode => _directMode ? "DIRECT" : "BATCH";

    /// <summary>
    /// Metrics data class
    /// </summary>
    public class InventoryMetrics
    {
        public long BatchModeRequests { get; set; }
        public long DirectModeRequests { get; set; }
        public long TotalRedisCalls { get; set; }
        public bool ModeSwitched { get; set; }
    }
}
