using FlashSale.Api.Models;

namespace FlashSale.Api.Services;

/// <summary>
/// Repository interface for Campaign SKU Allocations
/// </summary>
public interface ICampaignSkuAllocationRepository
{
    Task<List<CampaignSkuAllocation>> GetAvailableUnitsAsync(string campaignId, int maxUnits);
    Task<int> ClaimUnitsAsync(string serviceId, string campaignId, int maxUnits);
    Task<List<CampaignSkuAllocation>> GetClaimedUnitsAsync(string serviceId, string campaignId);
    Task ReleaseUnitsAsync(string serviceId);
}
