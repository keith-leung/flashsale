using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace FlashSale.Api.Models;

/// <summary>
/// Flash Sale Campaign (SPU-level) with total sale limit across all SKU variants
/// </summary>
[Table("flash_sale_campaigns")]
public class FlashSale : BaseEntity
{
    [Required]
    [StringLength(250)]
    public string Name { get; set; } = string.Empty;

    public string? Description { get; set; }

    [Required]
    public Guid SpuId { get; set; }

    [Required]
    [Range(1, int.MaxValue)]
    public int TotalSaleLimit { get; set; }

    public int SoldQuantity { get; set; } = 0;

    public int MaxQuantityPerCustomer { get; set; } = 1;

    [Required]
    [Column(TypeName = "decimal(10,2)")]
    public decimal FlashPrice { get; set; }

    [Required]
    public DateTime StartTime { get; set; }

    [Required]
    public DateTime EndTime { get; set; }

    [Required]
    [StringLength(20)]
    public string Status { get; set; } = "scheduled";

    public bool IsActive { get; set; } = true;

    // Navigation properties
    [ForeignKey("SpuId")]
    public virtual Spu? Spu { get; set; }

    public virtual ICollection<Order> Orders { get; set; } = new List<Order>();

    // Business logic methods
    public int RemainingQuantity => Math.Max(0, TotalSaleLimit - SoldQuantity);

    public bool IsTimeActive()
    {
        var now = DateTime.UtcNow;
        return StartTime <= now && EndTime >= now;
    }

    public bool IsAvailable()
    {
        return IsActive && Status == "active" && IsTimeActive() && RemainingQuantity > 0;
    }

    public double PercentageSold()
    {
        if (TotalSaleLimit == 0) return 0.0;
        return (SoldQuantity * 100.0) / TotalSaleLimit;
    }
}
