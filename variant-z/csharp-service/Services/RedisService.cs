using StackExchange.Redis;

namespace FlashSale.Services;

public interface IRedisService
{
    Task<RedisResult?> ExecuteLuaScriptAsync(string script, RedisKey[] keys, RedisValue[] args);
    Task<string?> StringGetAsync(string key);
    Task<bool> StringSetAsync(string key, string value, TimeSpan? expiry = null);
    Task<bool> SortedSetAddAsync(string key, string member, double score);
    Task<long> SortedSetLengthAsync(string key);
    Task<string?> SortedSetPopMinAsync(string key);
    Task<long> StringDecrementByAsync(string key, long value);
    Task<bool> KeyDeleteAsync(string key);
    IDatabase GetDatabase();
}

public class RedisService : IRedisService, IDisposable
{
    private readonly IConnectionMultiplexer _redis;
    private readonly IDatabase _database;
    private readonly Dictionary<string, string> _luaScriptCache = new();

    public RedisService(IConfiguration configuration)
    {
        var host = configuration["Redis:Host"] ?? "localhost";
        var port = int.Parse(configuration["Redis:Port"] ?? "6379");
        var connectionString = $"{host}:{port}";

        var options = ConfigurationOptions.Parse(connectionString);
        options.AbortOnConnectFail = false;
        options.ConnectRetry = 3;
        options.ConnectTimeout = 5000;
        options.SyncTimeout = 5000;
        
        _redis = ConnectionMultiplexer.Connect(options);
        _database = _redis.GetDatabase();
    }

    public IDatabase GetDatabase()
    {
        return _database;
    }

    public async Task<RedisResult?> ExecuteLuaScriptAsync(string script, RedisKey[] keys, RedisValue[] args)
    {
        // Cache Lua scripts to avoid loading on every request
        var scriptHash = script.GetHashCode().ToString();
        
        if (!_luaScriptCache.TryGetValue(scriptHash, out var cachedScript))
        {
            cachedScript = script;
            _luaScriptCache[scriptHash] = cachedScript;
        }

        return await _database.ScriptEvaluateAsync(cachedScript, keys, args);
    }

    public async Task<string?> StringGetAsync(string key)
    {
        var value = await _database.StringGetAsync(key);
        return value.IsNullOrEmpty ? null : value.ToString();
    }

    public Task<bool> StringSetAsync(string key, string value, TimeSpan? expiry = null)
    {
        return _database.StringSetAsync(key, value, expiry);
    }

    public Task<bool> SortedSetAddAsync(string key, string member, double score)
    {
        return _database.SortedSetAddAsync(key, member, score);
    }

    public Task<long> SortedSetLengthAsync(string key)
    {
        return _database.SortedSetLengthAsync(key);
    }

    public async Task<string?> SortedSetPopMinAsync(string key)
    {
        var result = await _database.SortedSetPopAsync(key, Order.Ascending);
        return result?.Element.ToString();
    }

    public Task<long> StringDecrementByAsync(string key, long value)
    {
        return _database.StringDecrementAsync(key, value);
    }

    public Task<bool> KeyDeleteAsync(string key)
    {
        return _database.KeyDeleteAsync(key);
    }

    public void Dispose()
    {
        _redis?.Dispose();
    }
}