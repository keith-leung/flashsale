namespace FlashSale.Api.V.Models;

public class AuditOrderLog
{
    public Guid Id { get; set; }
    public Guid OrderId { get; set; }
    public string CustomerEmail { get; set; } = string.Empty;
    public Guid SkuId { get; set; }
    public int Quantity { get; set; }
    public decimal UnitPrice { get; set; }
    public Guid? FlashSaleCampaignId { get; set; }
    public AuditStatus Status { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? UpdatedAt { get; set; }
}

public enum AuditStatus
{
    PENDING,
    CONFIRMED,
    FAILED
}
