namespace FlashSale.Api.V.DTOs;

public class OrderDtos
{
    public class OrderCreateRequest
    {
        public string CustomerEmail { get; set; } = string.Empty;
        public string? SkuId { get; set; }
        public int Quantity { get; set; }
        public decimal UnitPrice { get; set; }
        public string? FlashSaleCampaignId { get; set; }
    }

    public class OrderCreateResponse
    {
        public Guid AuditId { get; set; }
        public Guid OrderId { get; set; }
        public string Status { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
    }

    public class OrderStatusResponse
    {
        public Guid AuditId { get; set; }
        public string Status { get; set; } = string.Empty;
        public DateTime CreatedAt { get; set; }
    }
}
