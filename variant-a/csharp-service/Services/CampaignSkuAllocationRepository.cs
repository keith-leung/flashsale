using FlashSale.Api.Data;
using FlashSale.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace FlashSale.Api.Services;

/// <summary>
/// Repository for managing Campaign SKU Allocation units
/// Handles atomic claiming and releasing of allocation units
/// </summary>
public class CampaignSkuAllocationRepository : ICampaignSkuAllocationRepository
{
    private readonly FlashSaleDbContext _context;
    private readonly ILogger<CampaignSkuAllocationRepository> _logger;

    public CampaignSkuAllocationRepository(
        FlashSaleDbContext context,
        ILogger<CampaignSkuAllocationRepository> logger)
    {
        _context = context;
        _logger = logger;
    }

    /// <summary>
    /// Get available allocation units for a campaign
    /// </summary>
    public async Task<List<CampaignSkuAllocation>> GetAvailableUnitsAsync(string campaignId, int maxUnits)
    {
        return await _context.CampaignSkuAllocations
            .Where(a => a.CampaignId == campaignId && a.Status == "available")
            .OrderBy(a => a.Id)
            .Take(maxUnits)
            .ToListAsync();
    }

    /// <summary>
    /// Atomically claim allocation units for this service instance
    /// Returns number of units successfully claimed
    /// </summary>
    public async Task<int> ClaimUnitsAsync(string serviceId, string campaignId, int maxUnits)
    {
        using var transaction = await _context.Database.BeginTransactionAsync();

        try
        {
            // Use raw SQL for atomic update with row locking
            var sql = @"
                UPDATE campaign_sku_allocations
                SET status = 'claimed',
                    claimed_by = {0},
                    claimed_at = {1},
                    updated_at = {1}
                WHERE campaign_id = {2}
                  AND status = 'available'
                  AND id IN (
                    SELECT id FROM (
                        SELECT id FROM campaign_sku_allocations
                        WHERE campaign_id = {2} AND status = 'available'
                        ORDER BY id
                        LIMIT {3}
                    ) AS tmp
                  )";

            var now = DateTime.UtcNow;
            var rowsAffected = await _context.Database.ExecuteSqlRawAsync(
                sql,
                serviceId,
                now,
                campaignId,
                maxUnits
            );

            await transaction.CommitAsync();

            _logger.LogInformation(
                "Service {ServiceId} claimed {Count} allocation units for campaign {CampaignId}",
                serviceId, rowsAffected, campaignId
            );

            return rowsAffected;
        }
        catch (Exception ex)
        {
            await transaction.RollbackAsync();
            _logger.LogError(ex,
                "Failed to claim allocation units for service {ServiceId}", serviceId);
            throw;
        }
    }

    /// <summary>
    /// Get all units claimed by this service instance
    /// </summary>
    public async Task<List<CampaignSkuAllocation>> GetClaimedUnitsAsync(string serviceId, string campaignId)
    {
        return await _context.CampaignSkuAllocations
            .Where(a => a.ClaimedBy == serviceId && a.CampaignId == campaignId)
            .OrderBy(a => a.Id)
            .ToListAsync();
    }

    /// <summary>
    /// Release all units claimed by this service instance (for graceful shutdown)
    /// </summary>
    public async Task ReleaseUnitsAsync(string serviceId)
    {
        using var transaction = await _context.Database.BeginTransactionAsync();

        try
        {
            var sql = @"
                UPDATE campaign_sku_allocations
                SET status = 'available',
                    claimed_by = NULL,
                    claimed_at = NULL,
                    updated_at = {0}
                WHERE claimed_by = {1}";

            var now = DateTime.UtcNow;
            var rowsAffected = await _context.Database.ExecuteSqlRawAsync(sql, now, serviceId);

            await transaction.CommitAsync();

            _logger.LogInformation(
                "Released {Count} allocation units for service {ServiceId}",
                rowsAffected, serviceId
            );
        }
        catch (Exception ex)
        {
            await transaction.RollbackAsync();
            _logger.LogError(ex,
                "Failed to release allocation units for service {ServiceId}", serviceId);
            throw;
        }
    }
}
