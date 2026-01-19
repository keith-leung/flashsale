namespace FlashSale.Models;

public class Sku : BaseEntity
{
    public Guid SpuId { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Attributes { get; set; }
    
    // Navigation properties
    public Spu Spu { get; set; } = null!;
    public Inventory? Inventory { get; set; }
    public ICollection<OrderLineItem> OrderLineItems { get; set; } = new List<OrderLineItem>();
}