using System.ComponentModel.DataAnnotations;

namespace FlashSale.Api.Models;

/// <summary>
/// Standard Product Unit - represents a product concept (like Saleor's Product)
/// </summary>
public class Spu : BaseEntity
{
    [Required]
    [MaxLength(250)]
    public string Name { get; set; } = string.Empty;
    
    [Required]
    [MaxLength(255)]
    public string Slug { get; set; } = string.Empty;
    
    public string? Description { get; set; }
    
    public bool IsActive { get; set; } = true;
    
    // Navigation properties
    public virtual ICollection<Sku> Skus { get; set; } = new List<Sku>();
    
    public override string ToString() => Name;
}
