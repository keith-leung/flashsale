namespace FlashSale.Models;

public class Inventory : BaseEntity
{
    public Guid SkuId { get; set; }
    public int Quantity { get; set; }
    
    // Navigation properties
    public Sku Sku { get; set; } = null!;
}