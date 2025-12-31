using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace FlashSale.Api.Models;

/// <summary>
/// Stock Keeping Unit - represents a specific variant of a product (like Saleor's ProductVariant)
/// </summary>
public class Sku : BaseEntity
{
    [Required]
    [MaxLength(255)]
    public string SkuCode { get; set; } = string.Empty;
    
    [MaxLength(255)]
    public string? Name { get; set; }
    
    [Required]
    public Guid SpuId { get; set; }
    
    [Column(TypeName = "decimal(10,2)")]
    public decimal Price { get; set; }
    
    [Column(TypeName = "decimal(10,2)")]
    public decimal? CostPrice { get; set; }
    
    [Column(TypeName = "decimal(8,3)")]
    public decimal? Weight { get; set; } // in kg
    
    public bool TrackInventory { get; set; } = true;
    
    public bool IsActive { get; set; } = true;
    
    // Navigation properties
    [ForeignKey(nameof(SpuId))]
    public virtual Spu Spu { get; set; } = null!;

    public virtual Inventory? Inventory { get; set; }

    public override string ToString() => SkuCode ?? $"SKU-{Id}";
}
