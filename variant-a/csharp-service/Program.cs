using FlashSale.Api.Common;
using FlashSale.Api.Data;
using FlashSale.Api.Services;
using FlashSaleAPI.Services;
using Microsoft.EntityFrameworkCore;
using Serilog;
using StackExchange.Redis;

// Optimize thread pool for high-throughput scenarios
ThreadPool.SetMinThreads(200, 200);

var builder = WebApplication.CreateBuilder(args);

// Add Serilog
Log.Logger = new LoggerConfiguration()
    .ReadFrom.Configuration(builder.Configuration)
    .CreateLogger();

builder.Host.UseSerilog();

// Add services to the container.
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy = new SnakeCaseNamingPolicy();
    });
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new() { Title = "Flash Sale API", Version = "v1" });
});

// Database
builder.Services.AddDbContext<FlashSaleDbContext>(options =>
    options.UseMySql(builder.Configuration.GetConnectionString("DefaultConnection"),
        new MySqlServerVersion(new Version(8, 0)))
    .UseSnakeCaseNamingConvention());
// Redis
builder.Services.AddSingleton<IConnectionMultiplexer>(provider =>
{
    if (Environment.GetEnvironmentVariable("BENCHMARK_MODE") == "true")
    {
        // Return a disconnected multiplexer that won't throw on connect
        var config = ConfigurationOptions.Parse("localhost:6379,abortConnect=false");
        return ConnectionMultiplexer.Connect(config);
    }

    var connectionString = builder.Configuration.GetConnectionString("Redis") ?? "localhost:6379";
    return ConnectionMultiplexer.Connect(connectionString);
});

// Variant A: Dual-layer Campaign Memory Allocator (SPU + SKU)
builder.Services.AddSingleton<CampaignMemoryAllocator>();

// AutoMapper
builder.Services.AddAutoMapper(typeof(Program));

// Snowflake ID Generator
var instanceId = builder.Configuration.GetValue<int>("App:InstanceId", 1);
builder.Services.AddSingleton(new CSharpSnowflakeGenerator(instanceId));

// Services
builder.Services.AddScoped<RedisCacheService>();
builder.Services.AddScoped<ISpuService, SpuService>();
builder.Services.AddScoped<ISkuService, SkuService>();
builder.Services.AddScoped<IFlashSaleService, FlashSaleService>();
builder.Services.AddScoped<IInventoryService, InventoryService>();
builder.Services.AddScoped<IOrderService, OrderService>();

// Background Services
if (Environment.GetEnvironmentVariable("BENCHMARK_MODE") != "true")
{
    builder.Services.AddHostedService<FlashSaleStatusUpdateService>();
    builder.Services.AddHostedService<OrderWritebackService>();
}
else 
{
    Log.Warning("BENCHMARK MODE: Background services disabled");
}

// CORS
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

// app.UseHttpsRedirection();
app.UseCors();
app.UseAuthorization();
app.MapControllers();

// Ensure database is created
if (Environment.GetEnvironmentVariable("BENCHMARK_MODE") != "true")
{
    using (var scope = app.Services.CreateScope())
    {
        try 
        {
            var context = scope.ServiceProvider.GetRequiredService<FlashSaleDbContext>();
            await context.Database.EnsureCreatedAsync();
        }
        catch (Exception ex)
        {
            Log.Error(ex, "Failed to initialize database");
        }
    }

    // VARIANT A: Initialize CampaignMemoryAllocator with dual-layer (SPU + SKU)
    using (var scope = app.Services.CreateScope())
    {
        var allocator = app.Services.GetRequiredService<CampaignMemoryAllocator>();
        var context = scope.ServiceProvider.GetRequiredService<FlashSaleDbContext>();

        Log.Information("Initializing Variant A: Loading active campaigns with dual-layer allocation...");

        try
        {
            // Load valid campaign IDs using raw ADO.NET with CAST to avoid Guid parsing issues
            var validCampaignIds = new List<Guid>();

            // Helper function to validate UUID format
            static bool IsValidUuid(string value)
            {
                if (string.IsNullOrEmpty(value) || value.Length != 36)
                    return false;

                // Check format: 8-4-4-4-12 with valid hex characters
                for (int i = 0; i < value.Length; i++)
                {
                    char c = value[i];
                    if (i == 8 || i == 13 || i == 18 || i == 23)
                    {
                        if (c != '-') return false;
                    }
                    else
                    {
                        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')))
                            return false;
                    }
                }
                return true;
            }

            // First, get valid campaign IDs using raw SQL (using a separate connection)
            var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
            using (var rawConnection = new MySqlConnector.MySqlConnection(connectionString))
            {
                await rawConnection.OpenAsync();
                using var command = rawConnection.CreateCommand();
                // Select as string using CAST to avoid MySqlConnector Guid parsing issues
                command.CommandText = @"
                    SELECT DISTINCT CAST(fsc.id AS CHAR(36)) as campaign_id,
                           CAST(fsc.spu_id AS CHAR(36)) as spu_id
                    FROM flash_sale_campaigns fsc
                    WHERE fsc.status = 'active'
                      AND fsc.is_active = 1
                ";

                using var reader = await command.ExecuteReaderAsync();
                while (await reader.ReadAsync())
                {
                    var campaignIdStr = reader.GetString(0);
                    var spuIdStr = reader.GetString(1);

                    // Validate both are proper UUIDs (hexadecimal characters only, proper format)
                    if (IsValidUuid(campaignIdStr) && IsValidUuid(spuIdStr))
                    {
                        validCampaignIds.Add(Guid.Parse(campaignIdStr));
                    }
                    else
                    {
                        Log.Debug("Skipping invalid campaign: id={CampaignId}, spu_id={SpuId}", campaignIdStr, spuIdStr);
                    }
                }
            }

            Log.Information("Found {Count} valid campaign IDs", validCampaignIds.Count);

            var campaigns = new List<FlashSale.Api.Models.FlashSale>();
            foreach (var campaignId in validCampaignIds)
            {
                try
                {
                    var campaign = await context.FlashSaleCampaigns
                        .Include(c => c.Spu)
                            .ThenInclude(spu => spu!.Skus.Where(sku => sku.IsActive))
                        .FirstOrDefaultAsync(c => c.Id == campaignId);

                    if (campaign != null)
                    {
                        campaigns.Add(campaign);
                    }
                }
                catch (Exception ex)
                {
                    Log.Warning(ex, "Failed to load campaign {CampaignId}, skipping", campaignId);
                }
            }

            int loadedCampaigns = 0;
            foreach (var campaign in campaigns)
            {
                try
                {
                    // Calculate C# allocation based on ratios
                    int totalLimit = campaign.TotalSaleLimit;
                    double preAllocPct = campaign.PreallocatePercentage / 100.0;
                    int totalRatio = campaign.CsharpAllocationRatio + campaign.JavaAllocationRatio + campaign.PythonAllocationRatio;

                    if (totalRatio == 0) totalRatio = 34; // Default: 20 + 13 + 1

                    int csharpAllocation = (int)(totalLimit * preAllocPct * campaign.CsharpAllocationRatio / totalRatio);

                    // Get SKUs for this campaign's SPU
                    var skus = campaign.Spu?.Skus?.Where(s => s.IsActive).ToList();
                    if (skus == null || skus.Count == 0)
                    {
                        Log.Warning("Campaign {CampaignId} has no active SKUs, skipping", campaign.Id);
                        continue;
                    }

                    // Distribute allocation evenly across SKUs
                    var skuAllocations = new Dictionary<Guid, int>();
                    int perSkuAllocation = csharpAllocation / skus.Count;
                    int remainder = csharpAllocation % skus.Count;

                    foreach (var sku in skus)
                    {
                        int allocation = perSkuAllocation + (remainder-- > 0 ? 1 : 0);
                        skuAllocations[sku.Id] = allocation;
                    }

                    // Get ordinary price from first SKU
                    decimal ordinaryPrice = skus.First().Price;

                    // Load campaign into allocator (Producer-Consumer v2 with Lua scripts)
                    allocator.LoadCampaign(
                        campaign.Id,
                        campaign.SpuId,
                        skuAllocations,
                        campaign.FlashPrice,
                        ordinaryPrice,
                        campaign.RefillLowerWatermarkPct
                    );

                    loadedCampaigns++;
                    Log.Information(
                        "Campaign {CampaignId} loaded: {CsharpAllocation} items across {SkuCount} SKUs (flash: {FlashPrice}, ordinary: {OrdinaryPrice})",
                        campaign.Id, csharpAllocation, skus.Count, campaign.FlashPrice, ordinaryPrice
                    );
                }
                catch (Exception ex)
                {
                    Log.Error(ex, "Failed to load campaign {CampaignId}", campaign.Id);
                }
            }

            if (loadedCampaigns > 0)
            {
                Log.Information("Variant A initialized: {LoadedCount} campaigns loaded with dual-layer (SPU + SKU) allocation", loadedCampaigns);
            }
            else
            {
                Log.Warning("Variant A: No active campaigns found. Orders will fall back to Variant Y (database).");
            }
        }
        catch (Exception ex)
        {
            Log.Error(ex, "Failed to initialize campaigns");
        }
    }
}
else
{
    Log.Warning("BENCHMARK MODE ENABLED: Skipping Database and Campaign Initialization");
}

Log.Information("Flash Sale API - Variant A started");

app.Run();
