using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace FlashSale.Api.Models;

/// <summary>
/// Inventory tracking for SKUs
/// </summary>
public class Inventory : BaseEntity
{
    [Required]
    public Guid SkuId { get; set; }
    
    public int Quantity { get; set; } = 0;
    
    public int ReservedQuantity { get; set; } = 0; // Items in pending orders
    
    public bool AllowNegativeStock { get; set; } = false;
    
    // Navigation properties
    [ForeignKey(nameof(SkuId))]
    public virtual Sku Sku { get; set; } = null!;
    
    // Calculated properties
    [NotMapped]
    public int AvailableQuantity => Math.Max(0, Quantity - ReservedQuantity);
    
    public bool CanFulfillQuantity(int requestedQuantity)
    {
        if (AllowNegativeStock) return true;
        return AvailableQuantity >= requestedQuantity;
    }
    
    public bool ReserveQuantity(int quantity)
    {
        if (!CanFulfillQuantity(quantity)) return false;
        ReservedQuantity += quantity;
        return true;
    }
    
    public void ReleaseQuantity(int quantity)
    {
        ReservedQuantity = Math.Max(0, ReservedQuantity - quantity);
    }
    
    public bool FulfillQuantity(int quantity)
    {
        if (ReservedQuantity < quantity) return false;
        ReservedQuantity -= quantity;
        Quantity -= quantity;
        return true;
    }
    
    public override string ToString() => $"Inventory for {Sku?.SkuCode}: {AvailableQuantity}/{Quantity}";
}
