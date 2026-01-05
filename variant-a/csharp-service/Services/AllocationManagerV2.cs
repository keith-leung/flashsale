using FlashSale.Api.Models;
using StackExchange.Redis;
using System.Collections.Concurrent;
using System.Net;

namespace FlashSale.Api.Services;

/// <summary>
/// Allocation Manager V2 - Claims and manages allocation units for service instances
///
/// Responsibilities:
/// - Claim allocation units from database on startup
/// - Load claimed units into AdaptiveInventoryV2 managers
/// - Provide access to adaptive inventory instances
/// </summary>
public class AllocationManagerV2
{
    private readonly ILogger<AllocationManagerV2> _logger;
    private readonly ICampaignSkuAllocationRepository _allocationRepository;
    private readonly IDatabase _redis;
    private readonly IServiceProvider _serviceProvider;

    // Service instance ID (unique per container/pod)
    private readonly string _serviceId;

    // Map of SKU ID → AdaptiveInventoryV2 instance
    private readonly ConcurrentDictionary<Guid, AdaptiveInventoryV2> _inventoryManagers = new();

    // Track claimed allocation IDs
    private readonly List<long> _claimedAllocationIds = new();

    public AllocationManagerV2(
        ILogger<AllocationManagerV2> logger,
        ICampaignSkuAllocationRepository allocationRepository,
        IConnectionMultiplexer redis,
        IServiceProvider serviceProvider)
    {
        _logger = logger;
        _allocationRepository = allocationRepository;
        _redis = redis.GetDatabase();
        _serviceProvider = serviceProvider;

        // Generate unique service ID (hostname + UUID)
        _serviceId = GenerateServiceId();
    }

    /// <summary>
    /// Generate unique service ID for this instance
    /// Format: csharp-{hostname}-{uuid}
    /// </summary>
    private string GenerateServiceId()
    {
        try
        {
            string hostname = Dns.GetHostName();
            string shortUuid = Guid.NewGuid().ToString()[..12];
            return $"csharp-{hostname}-{shortUuid}";
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to get hostname, using UUID only");
            return $"csharp-{Guid.NewGuid().ToString()[..12]}";
        }
    }

    /// <summary>
    /// Claim allocation units and load into memory
    /// </summary>
    public async Task<int> ClaimAndLoadAllocationsAsync(Guid campaignId)
    {
        _logger.LogInformation("============================================================");
        _logger.LogInformation("VARIANT A: Initializing Adaptive Inventory System");
        _logger.LogInformation("============================================================");
        _logger.LogInformation("Service ID: {ServiceId}", _serviceId);

        // Determine max units to claim based on service capacity
        int maxUnits = GetMaxUnitsForService();
        _logger.LogInformation("Attempting to claim up to {MaxUnits} allocation units...", maxUnits);

        // Claim units atomically from database
        int claimedCount = await _allocationRepository.ClaimUnitsAsync(
            _serviceId,
            campaignId.ToString(),
            maxUnits
        );

        if (claimedCount == 0)
        {
            _logger.LogWarning("No allocation units available to claim for campaign {CampaignId}", campaignId);
            return 0;
        }

        _logger.LogInformation("Successfully claimed {ClaimedCount} allocation units", claimedCount);

        // Load claimed units into memory
        var claimedUnits = await _allocationRepository.GetClaimedUnitsAsync(
            _serviceId,
            campaignId.ToString()
        );

        _logger.LogInformation("Loading {Count} allocation units into RAM...", claimedUnits.Count);

        foreach (var unit in claimedUnits)
        {
            try
            {
                // Create logger for this specific inventory instance
                var inventoryLogger = _serviceProvider.GetRequiredService<ILogger<AdaptiveInventoryV2>>();

                // Create AdaptiveInventoryV2 instance
                var inventory = new AdaptiveInventoryV2(
                    unit.Id,
                    Guid.Parse(unit.CampaignId),
                    Guid.Parse(unit.SkuId),
                    unit.AllocatedQuantity,
                    unit.RefillBatchSize,
                    unit.LowWaterMarkPct,
                    _redis,
                    inventoryLogger
                );

                // Store in map (SKU ID → inventory)
                _inventoryManagers[Guid.Parse(unit.SkuId)] = inventory;
                _claimedAllocationIds.Add(unit.Id);

                _logger.LogInformation(
                    "  Loaded allocation unit {AllocationId}: SKU={SkuId}, qty={Qty}, refill={Refill}, low_water={LowWater}%",
                    unit.Id, unit.SkuId, unit.AllocatedQuantity, unit.RefillBatchSize, unit.LowWaterMarkPct * 100
                );
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "Failed to load allocation unit {AllocationId}", unit.Id);
            }
        }

        _logger.LogInformation("============================================================");
        _logger.LogInformation("Successfully claimed and loaded {Count} allocation units into RAM", claimedUnits.Count);
        _logger.LogInformation("Total items in RAM: {TotalItems}",
            claimedUnits.Sum(u => u.AllocatedQuantity));
        _logger.LogInformation("============================================================");

        return claimedCount;
    }

    /// <summary>
    /// Get adaptive inventory manager for a SKU
    /// </summary>
    public AdaptiveInventoryV2? GetInventoryForSku(Guid skuId)
    {
        _inventoryManagers.TryGetValue(skuId, out var inventory);
        return inventory;
    }

    /// <summary>
    /// Check if this service has claimed units for a SKU
    /// </summary>
    public bool HasInventoryForSku(Guid skuId)
    {
        return _inventoryManagers.ContainsKey(skuId);
    }

    /// <summary>
    /// Get all metrics for monitoring
    /// </summary>
    public Dictionary<Guid, AdaptiveInventoryMetrics> GetAllMetrics()
    {
        var metrics = new Dictionary<Guid, AdaptiveInventoryMetrics>();

        foreach (var entry in _inventoryManagers)
        {
            metrics[entry.Key] = entry.Value.GetMetrics();
        }

        return metrics;
    }

    /// <summary>
    /// Determine max units to claim based on service capacity
    /// Can be configured via environment variable or use defaults
    /// </summary>
    private int GetMaxUnitsForService()
    {
        // Try to read from environment variable
        string? maxUnitsEnv = Environment.GetEnvironmentVariable("MAX_ALLOCATION_UNITS");
        if (!string.IsNullOrEmpty(maxUnitsEnv) && int.TryParse(maxUnitsEnv, out int maxUnits))
        {
            return maxUnits;
        }

        // Default: claim 2-4 units based on available CPU cores
        int cpuCores = Environment.ProcessorCount;
        if (cpuCores >= 8)
        {
            return 4;  // High-capacity server
        }
        else if (cpuCores >= 4)
        {
            return 2;  // Medium-capacity server
        }
        else
        {
            return 2;  // Low-capacity server
        }
    }

    /// <summary>
    /// Release all claimed allocation units (for graceful shutdown)
    /// </summary>
    public async Task ReleaseAllAllocationsAsync()
    {
        _logger.LogInformation("Releasing all claimed allocation units for service {ServiceId}...", _serviceId);

        await _allocationRepository.ReleaseUnitsAsync(_serviceId);

        _inventoryManagers.Clear();
        _claimedAllocationIds.Clear();

        _logger.LogInformation("All allocation units released successfully");
    }
}
