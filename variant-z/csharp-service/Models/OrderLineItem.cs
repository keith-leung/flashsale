namespace FlashSale.Models;

public class OrderLineItem : BaseEntity
{
    public Guid OrderId { get; set; }
    public Guid SkuId { get; set; }
    public int Quantity { get; set; }
    public decimal UnitPrice { get; set; }
    
    // Navigation properties
    public Order Order { get; set; } = null!;
    public Sku Sku { get; set; } = null!;
}