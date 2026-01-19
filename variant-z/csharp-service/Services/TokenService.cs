using FlashSale.Data;
using FlashSale.Models;
using Microsoft.EntityFrameworkCore;
using Newtonsoft.Json;
using StackExchange.Redis;

namespace FlashSale.Services;

public interface ITokenService
{
    Task PreAllocateTokensAsync(Guid campaignId, int totalLimit);
    Task<Dictionary<string, object>> AcquireTokenAsync(Guid campaignId, Guid skuId, int quantity);
    Task CacheSkuInventoryAsync(Guid skuId, int quantity);
    Task<int?> GetCachedSkuInventoryAsync(Guid skuId);
    Task<FlashSaleCampaign?> GetActiveCampaignForSpuAsync(Guid spuId);
}

public class TokenService : ITokenService
{
    private readonly IRedisService _redis;
    private readonly FlashSaleDbContext _dbContext;
    private readonly ILogger<TokenService> _logger;

    public TokenService(IRedisService redis, FlashSaleDbContext dbContext, ILogger<TokenService> logger)
    {
        _redis = redis;
        _dbContext = dbContext;
        _logger = logger;
    }

    public async Task PreAllocateTokensAsync(Guid campaignId, int totalLimit)
    {
        var campaign = await _dbContext.FlashSaleCampaigns
            .Include(c => c.Spu)
            .ThenInclude(s => s.Skus)
            .ThenInclude(s => s.Inventory)
            .FirstOrDefaultAsync(c => c.Id == campaignId);

        if (campaign == null)
        {
            throw new ArgumentException($"Campaign {campaignId} not found");
        }

        var skus = campaign.Spu.Skus.ToList();
        var totalInventory = skus.Sum(s => s.Inventory?.Quantity ?? 0);

        if (totalInventory == 0)
        {
            throw new ArgumentException("No inventory available for campaign");
        }

        var db = _redis.GetDatabase();
        var tokenKey = $"campaign:{campaignId}:tokens";
        var metadataKey = $"campaign:{campaignId}:metadata";

        // Clear existing tokens
        await db.KeyDeleteAsync(tokenKey);
        await db.KeyDeleteAsync(metadataKey);

        // Distribute tokens proportionally to SKU inventory
        var tokenIndex = 0;
        foreach (var sku in skus)
        {
            var skuInventory = sku.Inventory?.Quantity ?? 0;
            if (skuInventory == 0) continue;

            var skuTokenCount = Math.Min(
                skuInventory,
                (int)(totalLimit * ((double)skuInventory / totalInventory))
            );

            for (int i = 0; i < skuTokenCount; i++)
            {
                var tokenId = $"token_{Guid.NewGuid()}_{sku.Id}";
                await db.SortedSetAddAsync(tokenKey, tokenId, tokenIndex++);
            }

            // Cache SKU inventory (NO TTL - inventory is source of truth)
            await db.StringSetAsync($"sku:{sku.Id}:inventory", skuInventory.ToString());
        }

        // Cache campaign metadata (60s TTL)
        var metadata = new
        {
            total_tokens = totalLimit,
            remaining_tokens = totalLimit,
            status = "active"
        };
        await db.StringSetAsync(metadataKey, JsonConvert.SerializeObject(metadata), TimeSpan.FromSeconds(60));

        _logger.LogInformation("Pre-allocated {Count} tokens for campaign {CampaignId}", tokenIndex, campaignId);
    }

    public async Task<Dictionary<string, object>> AcquireTokenAsync(Guid campaignId, Guid skuId, int quantity)
    {
        var db = _redis.GetDatabase();
        var tokenKey = $"campaign:{campaignId}:tokens";
        var skuKey = $"sku:{skuId}:inventory";
        var metadataKey = $"campaign:{campaignId}:metadata";

        // Load and execute Lua script
        var script = await File.ReadAllTextAsync("Resources/acquire_order_token.lua");
        var keys = new RedisKey[] { tokenKey, skuKey, metadataKey };
        var args = new RedisValue[] { quantity.ToString(), campaignId.ToString() };

        var result = await _redis.ExecuteLuaScriptAsync(script, keys, args);

        if (result == null)
        {
            return new Dictionary<string, object> { { "err", "LUA_SCRIPT_ERROR" } };
        }

        var resultArray = (RedisResult[])result;
        var resultType = resultArray[0].ToString();

        if (resultType == "err")
        {
            return new Dictionary<string, object> { { "err", resultArray[1].ToString() } };
        }

        return new Dictionary<string, object>
        {
            { "ok", resultArray[1].ToString() },
            { "remaining_stock", long.Parse(resultArray[2].ToString()!) }
        };
    }

    public async Task CacheSkuInventoryAsync(Guid skuId, int quantity)
    {
        var key = $"sku:{skuId}:inventory";
        await _redis.StringSetAsync(key, quantity.ToString());
    }

    public async Task<int?> GetCachedSkuInventoryAsync(Guid skuId)
    {
        var key = $"sku:{skuId}:inventory";
        var redisValue = await _redis.StringGetAsync(key);
        return !string.IsNullOrEmpty(redisValue) ? int.Parse(redisValue!) : null;
    }

    public async Task<FlashSaleCampaign?> GetActiveCampaignForSpuAsync(Guid spuId)
    {
        var now = DateTime.UtcNow;
        return await _dbContext.FlashSaleCampaigns
            .FirstOrDefaultAsync(c => 
                c.SpuId == spuId && 
                c.Status == "active" &&
                c.StartTime <= now &&
                c.EndTime >= now);
    }
}