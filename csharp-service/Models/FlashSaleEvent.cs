using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace FlashSale.Api.Models;

/// <summary>
/// Flash Sale Campaign - SPU-level (product family) with time-based controls and sale limits.
///
/// CRITICAL: Campaigns are SPU-level, NOT SKU-level!
/// Example: Campaign for "iPhone 16" (SPU) with 100K total_sale_limit
///          Customers order "iPhone 16 Black 512GB" or "iPhone 16 Silver 128GB" (SKUs)
///          Campaign tracks total across ALL SKUs under the SPU
/// </summary>
[Table("flash_sale_campaigns")]
public class FlashSaleCampaign : BaseEntity
{
    [Required]
    [MaxLength(250)]
    public string Name { get; set; } = string.Empty;

    public string? Description { get; set; }

    [Required]
    public Guid SpuId { get; set; }  // Links to product family (SPU), NOT variant (SKU)!

    [Required]
    public int TotalSaleLimit { get; set; } // Total units across ALL SKUs under this SPU

    public int SoldQuantity { get; set; } = 0; // Incremented when ANY SKU under this SPU is ordered

    public int MaxQuantityPerCustomer { get; set; } = 1; // Max per customer

    [Required]
    [Column(TypeName = "decimal(10,2)")]
    public decimal FlashPrice { get; set; } // Special campaign price (cheaper than regular SKU price)

    [Required]
    public DateTime StartTime { get; set; }
    
    [Required]
    public DateTime EndTime { get; set; }
    
    public FlashSaleStatus Status { get; set; } = FlashSaleStatus.Scheduled;
    
    public bool IsActive { get; set; } = true;

    // Navigation properties
    [ForeignKey(nameof(SpuId))]
    public virtual Spu Spu { get; set; } = null!;  // Links to product family
    public virtual ICollection<Order> Orders { get; set; } = new List<Order>();
    
    // Calculated properties
    [NotMapped]
    public int RemainingQuantity => Math.Max(0, TotalSaleLimit - SoldQuantity);
    
    [NotMapped]
    public bool IsTimeActive
    {
        get
        {
            var now = DateTime.UtcNow;
            return StartTime <= now && now <= EndTime;
        }
    }
    
    [NotMapped]
    public bool IsAvailable => IsActive && Status == FlashSaleStatus.Active && IsTimeActive && RemainingQuantity > 0;
    
    public bool CanPurchaseQuantity(int quantity)
    {
        if (!IsAvailable) return false;
        if (quantity > MaxQuantityPerCustomer) return false;
        return RemainingQuantity >= quantity;
    }
    
    public bool PurchaseQuantity(int quantity)
    {
        if (!CanPurchaseQuantity(quantity)) return false;
        
        SoldQuantity += quantity;
        
        // Update status if sold out
        if (RemainingQuantity == 0)
        {
            Status = FlashSaleStatus.Ended;
        }
        
        return true;
    }
    
    public void UpdateStatus()
    {
        var now = DateTime.UtcNow;
        
        if (Status == FlashSaleStatus.Cancelled) return; // Don't change cancelled status
        
        if (now < StartTime)
        {
            Status = FlashSaleStatus.Scheduled;
        }
        else if (now > EndTime || RemainingQuantity == 0)
        {
            Status = FlashSaleStatus.Ended;
        }
        else
        {
            Status = FlashSaleStatus.Active;
        }
    }
    
    public override string ToString() => $"{Name} ({Status})";
}

public enum FlashSaleStatus
{
    Scheduled,
    Active,
    Ended,
    Cancelled
}
