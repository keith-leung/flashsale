namespace FlashSale.Models;

public class Order : BaseEntity
{
    public string OrderNumber { get; set; } = string.Empty;
    public string CustomerName { get; set; } = string.Empty;
    public string CustomerEmail { get; set; } = string.Empty;
    public string Status { get; set; } = "created";
    public decimal TotalAmount { get; set; }
    
    // Navigation properties
    public ICollection<OrderLineItem> LineItems { get; set; } = new List<OrderLineItem>();
    public ICollection<Payment> Payments { get; set; } = new List<Payment>();
}