namespace FlashSale.Models;

public class Spu : BaseEntity
{
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    
    // Navigation properties
    public ICollection<Sku> Skus { get; set; } = new List<Sku>();
}