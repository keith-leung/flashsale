using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace FlashSale.Api.Models;

/// <summary>
/// Flash Sale Campaign (SPU-level) with total sale limit across all SKU variants
/// </summary>
[Table("flash_sales")]
public class FlashSale : BaseEntity
{
    [Required]
    [StringLength(255)]
    [Column("campaign_name")]
    public string CampaignName { get; set; } = string.Empty;

    [Required]
    [Column("spu_id")]
    public Guid SpuId { get; set; }

    [Required]
    [Range(1, int.MaxValue)]
    [Column("total_sale_limit")]
    public int TotalSaleLimit { get; set; }

    [Column("sold_count")]
    public int SoldCount { get; set; } = 0;

    [Required]
    [Column("start_time")]
    public DateTime StartTime { get; set; }

    [Required]
    [Column("end_time")]
    public DateTime EndTime { get; set; }

    [Required]
    [Column("status")]
    public FlashSaleCampaignStatus Status { get; set; } = FlashSaleCampaignStatus.Pending;

    [Column("flash_sale_price", TypeName = "decimal(10,2)")]
    public decimal? FlashSalePrice { get; set; }

    [Range(1, int.MaxValue)]
    [Column("max_per_order")]
    public int MaxPerOrder { get; set; } = 10;

    // Navigation properties
    [ForeignKey("SpuId")]
    public virtual Spu? Spu { get; set; }

    // Business logic methods
    public int RemainingQuantity => Math.Max(0, TotalSaleLimit - SoldCount);

    public bool IsTimeActive()
    {
        var now = DateTime.UtcNow;
        return StartTime <= now && EndTime >= now;
    }

    public bool IsAvailable()
    {
        return Status == FlashSaleCampaignStatus.Active && IsTimeActive() && RemainingQuantity > 0;
    }

    public double PercentageSold()
    {
        if (TotalSaleLimit == 0) return 0.0;
        return (SoldCount * 100.0) / TotalSaleLimit;
    }
}

public enum FlashSaleCampaignStatus
{
    Pending,
    Active,
    SoldOut,
    Ended
}
