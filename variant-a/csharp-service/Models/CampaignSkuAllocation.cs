using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace FlashSale.Api.Models;

/// <summary>
/// Campaign SKU Allocation Unit - Variant A Database-Backed Allocation
///
/// Represents a pre-allocated inventory unit that can be claimed by service instances.
/// Each unit contains a fixed quantity of items that will be loaded into RAM.
/// </summary>
[Table("campaign_sku_allocations")]
public class CampaignSkuAllocation
{
    [Key]
    [Column("id")]
    public long Id { get; set; }

    [Column("campaign_id")]
    [MaxLength(36)]
    public string CampaignId { get; set; } = string.Empty;

    [Column("sku_id")]
    [MaxLength(36)]
    public string SkuId { get; set; } = string.Empty;

    /// <summary>
    /// Initial quantity allocated to this unit (e.g., 500)
    /// This amount will be loaded into RAM when claimed
    /// </summary>
    [Column("allocated_quantity")]
    public int AllocatedQuantity { get; set; }

    /// <summary>
    /// Batch size for async refills (e.g., 50)
    /// When hitting low water mark, refill this many items from campaign pool
    /// </summary>
    [Column("refill_batch_size")]
    public int RefillBatchSize { get; set; }

    /// <summary>
    /// Low water mark percentage as decimal (e.g., 0.30 for 30%)
    /// When local stock drops to this %, trigger async refill
    /// </summary>
    [Column("low_water_mark_pct")]
    public decimal LowWaterMarkPct { get; set; }

    /// <summary>
    /// Service instance ID that claimed this unit (e.g., "csharp-hostname-uuid")
    /// NULL if unit is available for claiming
    /// </summary>
    [Column("claimed_by")]
    [MaxLength(255)]
    public string? ClaimedBy { get; set; }

    /// <summary>
    /// Timestamp when this unit was claimed
    /// </summary>
    [Column("claimed_at")]
    public DateTime? ClaimedAt { get; set; }

    /// <summary>
    /// Status: 'available', 'claimed', 'depleted'
    /// </summary>
    [Column("status")]
    [MaxLength(20)]
    public string Status { get; set; } = "available";

    [Column("created_at")]
    public DateTime CreatedAt { get; set; }

    [Column("updated_at")]
    public DateTime UpdatedAt { get; set; }
}
