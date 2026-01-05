using StackExchange.Redis;
using System.Collections.Concurrent;

namespace FlashSale.Api.Services;

/// <summary>
/// Manages adaptive inventory services for multiple SKUs
/// Singleton pattern - one instance per application
/// </summary>
public class AdaptiveInventoryManager
{
    private readonly ILogger<AdaptiveInventoryManager> _logger;
    private readonly IDatabase _db;
    private string? _luaScriptSha;
    private readonly ConcurrentDictionary<string, AdaptiveInventoryService> _services = new();
    private readonly SemaphoreSlim _initLock = new(1, 1);

    public AdaptiveInventoryManager(ILogger<AdaptiveInventoryManager> logger, IConnectionMultiplexer redis)
    {
        _logger = logger;
        _db = redis.GetDatabase();
    }

    /// <summary>
    /// Initialize and load Lua script into Redis
    /// </summary>
    public async Task InitializeAsync()
    {
        if (_luaScriptSha != null) return;

        await _initLock.WaitAsync();
        try
        {
            if (_luaScriptSha != null) return;

            // Load Lua script from file
            string scriptPath = Path.Combine(AppContext.BaseDirectory, "lua", "inventory_refill.lua");
            string scriptContent = await File.ReadAllTextAsync(scriptPath);

            // Load script into Redis
            var server = _db.Multiplexer.GetServer(_db.Multiplexer.GetEndPoints().First());
            var sha = await server.ScriptLoadAsync(scriptContent);
            _luaScriptSha = BitConverter.ToString(sha).Replace("-", "").ToLower();

            _logger.LogInformation("AdaptiveInventoryManager initialized");
            _logger.LogInformation("  Lua Script SHA: {LuaScriptSha}", _luaScriptSha);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to initialize AdaptiveInventoryManager");
            throw;
        }
        finally
        {
            _initLock.Release();
        }
    }

    /// <summary>
    /// Get or create adaptive inventory service for a SKU
    /// </summary>
    /// <param name="campaignId">Campaign ID</param>
    /// <param name="skuId">SKU ID</param>
    /// <returns>AdaptiveInventoryService instance for this SKU</returns>
    public async Task<AdaptiveInventoryService> GetServiceAsync(string campaignId, string skuId)
    {
        if (_luaScriptSha == null)
        {
            await InitializeAsync();
        }

        string serviceKey = $"{campaignId}:{skuId}";

        return _services.GetOrAdd(serviceKey, key =>
        {
            _logger.LogDebug("Creating new AdaptiveInventoryService for {ServiceKey}", serviceKey);
            return new AdaptiveInventoryService(
                campaignId,
                skuId,
                _db,
                _luaScriptSha!
            );
        });
    }

    /// <summary>
    /// Get metrics for all active services
    /// </summary>
    public Dictionary<string, Dictionary<string, object>> GetAllMetrics()
    {
        var metrics = new Dictionary<string, Dictionary<string, object>>();

        foreach (var entry in _services)
        {
            var m = entry.Value.GetMetrics();

            metrics[entry.Key] = new Dictionary<string, object>
            {
                ["batch_mode_requests"] = m.BatchModeRequests,
                ["direct_mode_requests"] = m.DirectModeRequests,
                ["total_redis_calls"] = m.TotalRedisCalls,
                ["mode_switched"] = m.ModeSwitched,
                ["current_mode"] = entry.Value.CurrentMode
            };
        }

        return metrics;
    }

    /// <summary>
    /// Get count of active services
    /// </summary>
    public int GetServiceCount() => _services.Count;
}
