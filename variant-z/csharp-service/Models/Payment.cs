namespace FlashSale.Models;

public class Payment : BaseEntity
{
    public Guid OrderId { get; set; }
    public decimal Amount { get; set; }
    public string Status { get; set; } = "pending";
    public string PaymentMethod { get; set; } = "test";
    
    // Navigation properties
    public Order Order { get; set; } = null!;
}