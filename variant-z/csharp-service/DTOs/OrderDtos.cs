namespace FlashSale.DTOs;

public class OrderRequest
{
    public string CustomerName { get; set; } = string.Empty;
    public string CustomerEmail { get; set; } = string.Empty;
    public List<OrderLineItemRequest> LineItems { get; set; } = new();
}

public class OrderLineItemRequest
{
    public Guid SkuId { get; set; }
    public int Quantity { get; set; }
}

public class OrderResponse
{
    public Guid OrderId { get; set; }
    public string OrderNumber { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public decimal TotalAmount { get; set; }
    public string CustomerEmail { get; set; } = string.Empty;
}

public class ErrorResponse
{
    public string Error { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
}