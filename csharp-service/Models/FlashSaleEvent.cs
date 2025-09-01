using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace FlashSale.Api.Models;

/// <summary>
/// Flash Sale Event with time-based controls and sale limits
/// </summary>
public class FlashSaleEvent : BaseEntity
{
    [Required]
    [MaxLength(250)]
    public string Name { get; set; } = string.Empty;
    
    public string? Description { get; set; }
    
    [Required]
    public Guid SkuId { get; set; }
    
    [Required]
    public int TotalSaleLimit { get; set; } // Total units available for this flash sale
    
    public int SoldQuantity { get; set; } = 0; // Units sold so far
    
    public int MaxQuantityPerCustomer { get; set; } = 1; // Max per customer
    
    [Required]
    public DateTime StartTime { get; set; }
    
    [Required]
    public DateTime EndTime { get; set; }
    
    public FlashSaleStatus Status { get; set; } = FlashSaleStatus.Scheduled;
    
    public bool IsActive { get; set; } = true;
    
    // Navigation properties
    [ForeignKey(nameof(SkuId))]
    public virtual Sku Sku { get; set; } = null!;
    
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
