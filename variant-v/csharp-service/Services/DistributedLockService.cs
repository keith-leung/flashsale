using StackExchange.Redis;

namespace FlashSale.Api.V.Services;

public class DistributedLockService
{
    private readonly RedisManager _redisManager;
    private readonly IConfiguration _config;
    
    public DistributedLockService(RedisManager redisManager, IConfiguration config)
    {
        _redisManager = redisManager;
        _config = config;
    }
    
    public async Task<LockGuard> AcquireLockAsync(string skuId)
    {
        return await AcquireLockAsync(new[] { skuId });
    }
    
    public async Task<LockGuard> AcquireLockAsync(string[] skuIds)
    {
        var lockValues = new List<string>();
        var databases = new List<IDatabase>();
        var lockKey = $"lock:order:{skuIds[0]}";
        
        try
        {
            foreach (var skuId in skuIds)
            {
                var db = _redisManager.GetDatabaseForSku(skuId);
                var lockValue = Guid.NewGuid().ToString();
                
                var acquired = await db.StringSetAsync(
                    lockKey, 
                    lockValue, 
                    TimeSpan.FromMilliseconds(_config.GetValue<int>("Lock:TtlMs", 100)),
                    When.NotExists
                );
                
                if (!acquired)
                {
                    throw new TimeoutException($"Failed to acquire lock for SKU: {skuId}");
                }
                
                lockValues.Add(lockValue);
                databases.Add(db);
            }
            
            return new LockGuard(lockValues, databases, lockKey);
        }
        catch
        {
            await ReleaseLocksAsync(databases, lockKey);
            throw;
        }
    }
    
    private async Task ReleaseLocksAsync(List<IDatabase> databases, string lockKey)
    {
        foreach (var db in databases)
        {
            try
            {
                await db.KeyDeleteAsync(lockKey);
            }
            catch
            {
                // Ignore unlock errors
            }
        }
    }
    
    public class LockGuard : IAsyncDisposable
    {
        private readonly List<string> _lockValues;
        private readonly List<IDatabase> _databases;
        private readonly string _lockKey;
        
        public LockGuard(List<string> lockValues, List<IDatabase> databases, string lockKey)
        {
            _lockValues = lockValues;
            _databases = databases;
            _lockKey = lockKey;
        }
        
        public async ValueTask DisposeAsync()
        {
            foreach (var db in _databases)
            {
                try
                {
                    await db.KeyDeleteAsync(_lockKey);
                }
                catch
                {
                    // Ignore unlock errors
                }
            }
        }
    }
}
