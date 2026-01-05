using FlashSale.Api.Common;
using FlashSale.Api.Data;
using FlashSale.Api.Services;
using Microsoft.EntityFrameworkCore;
using Serilog;
using StackExchange.Redis;

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
    var connectionString = builder.Configuration.GetConnectionString("Redis") ?? "localhost:6379";
    return ConnectionMultiplexer.Connect(connectionString);
});

// Variant A: Allocation-based Adaptive Inventory
builder.Services.AddScoped<ICampaignSkuAllocationRepository, CampaignSkuAllocationRepository>();
builder.Services.AddSingleton<AllocationManagerV2>();

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
builder.Services.AddHostedService<FlashSaleStatusUpdateService>();

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

app.UseHttpsRedirection();
app.UseCors();
app.UseAuthorization();
app.MapControllers();

// Ensure database is created
using (var scope = app.Services.CreateScope())
{
    var context = scope.ServiceProvider.GetRequiredService<FlashSaleDbContext>();
    await context.Database.EnsureCreatedAsync();
}

// VARIANT A: Initialize Allocation Manager and claim allocation units
using (var scope = app.Services.CreateScope())
{
    var allocationManager = scope.ServiceProvider.GetRequiredService<AllocationManagerV2>();

    // Default campaign ID (can be configured via environment variable)
    var campaignIdStr = builder.Configuration.GetValue<string>("App:DefaultCampaignId", "750e8400-e29b-41d4-a716-446655440000");
    var campaignId = Guid.Parse(campaignIdStr);

    Log.Information("Initializing Variant A: Claiming allocation units for campaign {CampaignId}...", campaignId);

    int claimedCount = await allocationManager.ClaimAndLoadAllocationsAsync(campaignId);

    if (claimedCount > 0)
    {
        Log.Information("Variant A initialized successfully: {ClaimedCount} allocation units loaded into RAM", claimedCount);
    }
    else
    {
        Log.Warning("Variant A: No allocation units available. Service will fall back to direct Redis mode.");
    }
}

Log.Information("Flash Sale API - Variant A started");

app.Run();
