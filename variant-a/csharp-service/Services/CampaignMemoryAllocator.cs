using StackExchange.Redis;
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace FlashSaleAPI.Services
{
    /// <summary>
    /// Variant A: High-Performance Adaptive Batching (Producer-Consumer Pattern)
    ///
    /// Architecture:
    /// - Each SKU has its own AdaptiveInventoryUnit with local RAM stock
    /// - Producer: Async refill task triggered at low water mark (non-blocking)
    /// - Consumer: Hot path serves from local RAM (~0ms latency)
    /// - Failover: RAM -> SpinWait -> Direct Redis DECR -> Ordinary Stock
    ///
    /// Redis Keys:
    /// - SKU Pool: fs:{campaign_id}:redis_pool:sku:{sku_id}
    /// - Ordinary Stock: inv:{sku_id}
    /// </summary>
    public class CampaignMemoryAllocator
    {
        private readonly ILogger<CampaignMemoryAllocator> _logger;
        private readonly IConnectionMultiplexer _redis;
        private readonly ConcurrentDictionary<Guid, AdaptiveInventoryUnit> _skuUnits;
        private readonly ConcurrentDictionary<Guid, CampaignConfig> _campaignConfigs;

        public CampaignMemoryAllocator(
            ILogger<CampaignMemoryAllocator> logger,
            IConnectionMultiplexer redis)
        {
            _logger = logger;
            _redis = redis;
            _skuUnits = new ConcurrentDictionary<Guid, AdaptiveInventoryUnit>();
            _campaignConfigs = new ConcurrentDictionary<Guid, CampaignConfig>();

            _logger.LogInformation("CampaignMemoryAllocator initialized (Producer-Consumer v2)");
        }

        /// <summary>
        /// Load a campaign and create AdaptiveInventoryUnit for each SKU
        /// </summary>
        public void LoadCampaign(
            Guid campaignId,
            Guid spuId,
            Dictionary<Guid, int> skuAllocations,
            decimal flashPrice,
            decimal ordinaryPrice,
            double refillWatermarkPct,
            int refillBatchSize = 500)
        {
            // Store campaign config
            _campaignConfigs[campaignId] = new CampaignConfig(
                campaignId, spuId, flashPrice, ordinaryPrice);

            // Create AdaptiveInventoryUnit for each SKU
            foreach (var entry in skuAllocations)
            {
                var skuId = entry.Key;
                var allocatedQuantity = entry.Value;

                var unit = new AdaptiveInventoryUnit(
                    campaignId,
                    skuId,
                    allocatedQuantity,
                    refillBatchSize,
                    refillWatermarkPct,
                    flashPrice,
                    ordinaryPrice,
                    _redis,
                    _logger
                );

                _skuUnits[skuId] = unit;

                _logger.LogInformation(
                    "SKU {SkuId} initialized: {Quantity} items, batch={BatchSize}, watermark={Watermark}%",
                    skuId, allocatedQuantity, refillBatchSize, refillWatermarkPct);
            }

            _logger.LogInformation(
                "Campaign {CampaignId} loaded: {SkuCount} SKUs, flash={FlashPrice}, ordinary={OrdinaryPrice}",
                campaignId, skuAllocations.Count, flashPrice, ordinaryPrice);
        }

        /// <summary>
        /// Reserve one item using Producer-Consumer pattern
        /// </summary>
        public ReservationResult ReserveItem(Guid campaignId, Guid skuId)
        {
            if (!_skuUnits.TryGetValue(skuId, out var unit))
            {
                _logger.LogWarning("SKU {SkuId} not allocated to this service", skuId);
                return new ReservationResult(false, "not_allocated", 0m);
            }

            return unit.ReserveItem();
        }

        /// <summary>
        /// Get metrics for monitoring
        /// </summary>
        public Dictionary<Guid, InventoryMetrics> GetMetrics()
        {
            var metrics = new Dictionary<Guid, InventoryMetrics>();
            foreach (var entry in _skuUnits)
            {
                metrics[entry.Key] = entry.Value.GetMetrics();
            }
            return metrics;
        }

        // ========================================
        // Inner Classes
        // ========================================

        public class CampaignConfig
        {
            public Guid CampaignId { get; }
            public Guid SpuId { get; }
            public decimal FlashPrice { get; }
            public decimal OrdinaryPrice { get; }

            public CampaignConfig(Guid campaignId, Guid spuId, decimal flashPrice, decimal ordinaryPrice)
            {
                CampaignId = campaignId;
                SpuId = spuId;
                FlashPrice = flashPrice;
                OrdinaryPrice = ordinaryPrice;
            }
        }

        public class ReservationResult
        {
            public bool Success { get; }
            public string PriceType { get; }  // campaign, ordinary, sold_out, not_allocated
            public decimal Price { get; }

            public ReservationResult(bool success, string priceType, decimal price)
            {
                Success = success;
                PriceType = priceType;
                Price = price;
            }
        }

        public class InventoryMetrics
        {
            public int LocalStock { get; set; }
            public int LowWaterMark { get; set; }
            public long TotalRequests { get; set; }
            public long RamHits { get; set; }
            public long RedisRefills { get; set; }
            public long RedisDirectHits { get; set; }
            public string RamHitRate { get; set; } = "0%";
        }
    }

    /// <summary>
    /// Per-SKU Adaptive Inventory Unit with Producer-Consumer Pattern
    ///
    /// Consumer: Hot path decrements local RAM stock (~0ms)
    /// Producer: Async refill from Redis SKU pool when watermark hit
    /// </summary>
    public class AdaptiveInventoryUnit
    {
        private readonly Guid _campaignId;
        private readonly Guid _skuId;
        private readonly IConnectionMultiplexer _redis;
        private readonly ILogger _logger;

        // Configuration
        private readonly int _initialQuantity;
        private readonly int _refillBatchSize;
        private readonly double _lowWaterMarkPct;
        private readonly decimal _flashPrice;
        private readonly decimal _ordinaryPrice;

        // Local memory counter (CONSUMER)
        private int _localStock;
        private readonly object _stockLock = new object();

        // Refill coordination (PRODUCER)
        private readonly SemaphoreSlim _refillSemaphore = new SemaphoreSlim(1, 1);
        private volatile bool _refillInProgress;
        private int _currentLowWaterMark;

        // Metrics
        private long _totalRequests;
        private long _ramHits;
        private long _redisRefills;
        private long _redisDirectHits;

        // Redis keys
        private readonly string _skuPoolKey;
        private readonly string _ordinaryStockKey;

        public AdaptiveInventoryUnit(
            Guid campaignId,
            Guid skuId,
            int allocatedQuantity,
            int refillBatchSize,
            double lowWaterMarkPct,
            decimal flashPrice,
            decimal ordinaryPrice,
            IConnectionMultiplexer redis,
            ILogger logger)
        {
            _campaignId = campaignId;
            _skuId = skuId;
            _redis = redis;
            _logger = logger;

            _initialQuantity = allocatedQuantity;
            _refillBatchSize = refillBatchSize;
            _lowWaterMarkPct = lowWaterMarkPct / 100.0;
            _flashPrice = flashPrice;
            _ordinaryPrice = ordinaryPrice;

            _localStock = allocatedQuantity;
            _currentLowWaterMark = (int)(allocatedQuantity * _lowWaterMarkPct);

            // Redis keys - CORRECT FORMAT for Variant A v2
            _skuPoolKey = $"fs:{campaignId}:redis_pool:sku:{skuId}";
            _ordinaryStockKey = $"inv:{skuId}";

            _logger.LogInformation(
                "[SKU {SkuId}] Initialized: {Quantity} items, watermark={WaterMark}, refill_source={Key}",
                skuId, allocatedQuantity, _currentLowWaterMark, _skuPoolKey);
        }

        /// <summary>
        /// Reserve one item (Producer-Consumer pattern)
        ///
        /// Returns: (success, price_type, price)
        /// </summary>
        public CampaignMemoryAllocator.ReservationResult ReserveItem()
        {
            Interlocked.Increment(ref _totalRequests);

            // ========================================
            // FAST PATH: Local RAM (Consumer - ~0ms)
            // ========================================
            lock (_stockLock)
            {
                if (_localStock > 0)
                {
                    _localStock--;
                    Interlocked.Increment(ref _ramHits);

                    // Check low water mark (trigger async refill)
                    if (_localStock == _currentLowWaterMark && !_refillInProgress)
                    {
                        // Fire and forget - async refill in background
                        _ = Task.Run(() => AsyncRefillAsync());
                    }

                    return new CampaignMemoryAllocator.ReservationResult(true, "campaign", _flashPrice);
                }
            }

            // ========================================
            // SLOW PATH: Handle depleted local stock
            // ========================================
            return HandleDepleted();
        }

        /// <summary>
        /// Handle local stock depletion (Failover Chain)
        ///
        /// 1. SpinWait if refill in progress (panic buffer)
        /// 2. Direct Redis DECR on SKU pool
        /// 3. Fallback to ordinary stock
        /// </summary>
        private CampaignMemoryAllocator.ReservationResult HandleDepleted()
        {
            // ========================================
            // TIER 2: Panic Buffer (SpinWait for refill)
            // ========================================
            if (_refillInProgress)
            {
                _logger.LogDebug("[SKU {SkuId}] Panic buffer: refill in progress, waiting...", _skuId);

                var startTime = DateTime.UtcNow;
                var maxWaitMs = 10;

                while ((DateTime.UtcNow - startTime).TotalMilliseconds < maxWaitMs)
                {
                    lock (_stockLock)
                    {
                        if (_localStock > 0)
                        {
                            _localStock--;
                            Interlocked.Increment(ref _ramHits);
                            _logger.LogDebug("[SKU {SkuId}] Panic buffer SUCCESS", _skuId);
                            return new CampaignMemoryAllocator.ReservationResult(true, "campaign", _flashPrice);
                        }
                    }
                    Thread.Sleep(1); // 1ms spin
                }

                _logger.LogDebug("[SKU {SkuId}] Panic buffer timeout, falling back to Redis", _skuId);
            }

            // ========================================
            // TIER 3: Direct Redis DECR (SKU Pool)
            // ========================================
            try
            {
                var db = _redis.GetDatabase();
                var remaining = db.StringDecrement(_skuPoolKey);

                if (remaining >= 0)
                {
                    Interlocked.Increment(ref _redisDirectHits);
                    _logger.LogInformation(
                        "[SKU {SkuId}] Redis SKU pool hit, remaining: {Remaining}",
                        _skuId, remaining);
                    return new CampaignMemoryAllocator.ReservationResult(true, "campaign", _flashPrice);
                }
                else
                {
                    // Rollback negative
                    db.StringIncrement(_skuPoolKey);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "[SKU {SkuId}] Redis SKU pool error", _skuId);
            }

            // ========================================
            // TIER 4: Ordinary Stock (Final Fallback)
            // ========================================
            try
            {
                var db = _redis.GetDatabase();
                var remaining = db.StringDecrement(_ordinaryStockKey);

                if (remaining >= 0)
                {
                    _logger.LogWarning(
                        "[SKU {SkuId}] BENCHMARK STOP: Fell back to ordinary stock, remaining: {Remaining}",
                        _skuId, remaining);
                    return new CampaignMemoryAllocator.ReservationResult(true, "ordinary", _ordinaryPrice);
                }
                else
                {
                    db.StringIncrement(_ordinaryStockKey);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "[SKU {SkuId}] Ordinary stock error", _skuId);
            }

            // Completely sold out
            return new CampaignMemoryAllocator.ReservationResult(false, "sold_out", 0m);
        }

        /// <summary>
        /// PRODUCER: Async refill from Redis SKU pool
        ///
        /// Uses semaphore for single-flight pattern
        /// Implements cascading low water marks
        /// </summary>
        private async Task AsyncRefillAsync()
        {
            // Try to acquire semaphore (single-flight)
            if (!await _refillSemaphore.WaitAsync(0))
            {
                _logger.LogDebug("[SKU {SkuId}] Refill already in progress, skipping", _skuId);
                return;
            }

            _refillInProgress = true;
            var refillStart = DateTime.UtcNow;

            try
            {
                var db = _redis.GetDatabase();

                // Check if refill worth it
                int currentStock;
                lock (_stockLock) { currentStock = _localStock; }

                if (currentStock < 10 && _refillBatchSize < 10)
                {
                    _logger.LogDebug("[SKU {SkuId}] Skipping refill: stock too small", _skuId);
                    return;
                }

                // DECRBY Redis SKU pool
                var remaining = await db.StringDecrementAsync(_skuPoolKey, _refillBatchSize);

                if (remaining >= 0)
                {
                    // Success: Add to local stock
                    lock (_stockLock)
                    {
                        var oldStock = _localStock;
                        _localStock += _refillBatchSize;

                        // Update cascading low water mark
                        _currentLowWaterMark = (int)(_localStock * _lowWaterMarkPct);

                        Interlocked.Increment(ref _redisRefills);

                        var latencyMs = (DateTime.UtcNow - refillStart).TotalMilliseconds;

                        _logger.LogInformation(
                            "[SKU {SkuId}] Refill SUCCESS: {OldStock} -> {NewStock} (+{Batch}), watermark={WaterMark}, pool={Pool}, latency={Latency:F2}ms",
                            _skuId, oldStock, _localStock, _refillBatchSize, _currentLowWaterMark, remaining, latencyMs);
                    }
                }
                else
                {
                    // Pool depleted, rollback
                    await db.StringIncrementAsync(_skuPoolKey, _refillBatchSize);
                    _logger.LogWarning("[SKU {SkuId}] Refill FAILED: SKU pool depleted", _skuId);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "[SKU {SkuId}] Refill error", _skuId);
            }
            finally
            {
                _refillInProgress = false;
                _refillSemaphore.Release();
            }
        }

        public CampaignMemoryAllocator.InventoryMetrics GetMetrics()
        {
            return new CampaignMemoryAllocator.InventoryMetrics
            {
                LocalStock = _localStock,
                LowWaterMark = _currentLowWaterMark,
                TotalRequests = _totalRequests,
                RamHits = _ramHits,
                RedisRefills = _redisRefills,
                RedisDirectHits = _redisDirectHits,
                RamHitRate = _totalRequests > 0
                    ? $"{(_ramHits * 100.0 / _totalRequests):F2}%"
                    : "0%"
            };
        }
    }
}
