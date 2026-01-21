using FlashSale.Api.V.DTOs;
using FlashSale.Api.V.Services;
using Microsoft.AspNetCore.Mvc;
using StackExchange.Redis;

namespace FlashSale.Api.V.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class OrdersController : ControllerBase
{
    private readonly AuditService _auditService;
    private readonly DistributedLockService _lockService;
    private readonly RedisManager _redisManager;
    private readonly ILogger<OrdersController> _logger;
    
    public OrdersController(
        AuditService auditService,
        DistributedLockService lockService,
        RedisManager redisManager,
        ILogger<OrdersController> logger)
    {
        _auditService = auditService;
        _lockService = lockService;
        _redisManager = redisManager;
        _logger = logger;
    }
    
    [HttpPost]
    public async Task<IActionResult> CreateOrder([FromBody] OrderDtos.OrderCreateRequest request)
    {
        var response = new OrderDtos.OrderCreateResponse();
        
        try
        {
            // Step 0: Early validation - Check campaign limits BEFORE creating audit
            var db = _redisManager.GetDatabaseForSku(request.SkuId.ToString());
            var campaignKey = $"campaign:{request.FlashSaleCampaignId}:total_sold";
            var totalLimitKey = $"campaign:{request.FlashSaleCampaignId}:total_limit";
            var skuKey = $"campaign:{request.FlashSaleCampaignId}:sku:{request.SkuId}:remaining";
            
            // Early check: campaign limit
            var totalSold = (long?)await db.StringGetAsync(campaignKey);
            var totalLimit = (long?)await db.StringGetAsync(totalLimitKey);
            
            if (totalSold.HasValue && totalLimit.HasValue && totalSold.Value >= totalLimit.Value)
            {
                response.Status = "FAILED";
                response.Message = "Campaign sold out";
                return Conflict(response);
            }
            
            // Early check: SKU remaining
            var skuRemaining = (long?)await db.StringGetAsync(skuKey);
            
            if (skuRemaining.HasValue && skuRemaining.Value < request.Quantity)
            {
                response.Status = "FAILED";
                response.Message = "Insufficient stock";
                return Conflict(response);
            }
            
            // Step 1: Create audit record (write-ahead logging) - only if validation passed
            var audit = await _auditService.CreateAuditRecordAsync(
                request.CustomerEmail,
                request.SkuId ?? string.Empty,
                request.Quantity,
                request.UnitPrice,
                request.FlashSaleCampaignId
            );
            
            response.AuditId = audit.Id;
            response.OrderId = audit.OrderId;
            
            // Step 2: Acquire distributed lock for the SKU
            await using (var lockGuard = await _lockService.AcquireLockAsync(request.SkuId ?? string.Empty))
            {
                // Re-validate after lock acquisition (double-check pattern)
                totalSold = (long?)await db.StringGetAsync(campaignKey);
                
                if (totalSold.HasValue && totalLimit.HasValue && totalSold.Value >= totalLimit.Value)
                {
                    await _auditService.FailAuditAsync(audit.Id, "Campaign limit exceeded");
                    response.Status = "FAILED";
                    response.Message = "Campaign sold out";
                    return Conflict(response);
                }
                
                skuRemaining = (long?)await db.StringGetAsync(skuKey);
                
                if (skuRemaining.HasValue && skuRemaining.Value < request.Quantity)
                {
                    await _auditService.FailAuditAsync(audit.Id, "Insufficient SKU stock");
                    response.Status = "FAILED";
                    response.Message = "Insufficient stock";
                    return Conflict(response);
                }
                
                // Step 3: Update Redis counters atomically (using StringIncrementAsync for campaign counter)
                long newTotalSold = (long)await db.StringIncrementAsync(campaignKey, request.Quantity);
                long newSkuRemaining = (skuRemaining ?? 0) - request.Quantity;
                
                // Verify increment didn't exceed limit
                if (totalLimit.HasValue && newTotalSold > totalLimit.Value)
                {
                    // Rollback: restore counter to previous value
                    await db.StringDecrementAsync(campaignKey, request.Quantity);
                    
                    // Fail audit and return conflict
                    await _auditService.FailAuditAsync(audit.Id, "Campaign limit exceeded");
                    response.Status = "FAILED";
                    response.Message = "Campaign sold out";
                    return Conflict(response);
                }
                
                await db.StringSetAsync(skuKey, newSkuRemaining);
                
                // Step 4: Confirm audit record
                await _auditService.ConfirmAuditAsync(audit.Id);
                
                response.Status = "CONFIRMED";
                response.Message = "Order created successfully";
                return CreatedAtAction(nameof(GetOrderStatus), new { auditId = audit.Id }, response);
            }
        }
        catch (TimeoutException)
        {
            await _auditService.FailAuditAsync(response.AuditId, "Lock acquisition timeout");
            response.Status = "FAILED";
            response.Message = "Lock timeout";
            return Conflict(response);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating order");
            if (response.AuditId != Guid.Empty)
            {
                await _auditService.FailAuditAsync(response.AuditId, ex.Message);
            }
            response.Status = "FAILED";
            response.Message = $"Internal error: {ex.Message}";
            return StatusCode(500, response);
        }
    }
    
    [HttpGet("{auditId}")]
    public async Task<IActionResult> GetOrderStatus(Guid auditId)
    {
        try
        {
            var audit = await _auditService.GetAuditByIdAsync(auditId);
            var response = new OrderDtos.OrderStatusResponse
            {
                AuditId = audit.Id,
                Status = audit.Status.ToString(),
                CreatedAt = audit.CreatedAt
            };
            return Ok(response);
        }
        catch (KeyNotFoundException)
        {
            return NotFound();
        }
    }
}
