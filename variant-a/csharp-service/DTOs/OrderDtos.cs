using System.ComponentModel.DataAnnotations;
using FlashSale.Api.Models;

namespace FlashSale.Api.DTOs;

public class OrderLineItemCreateDto
{
    [Required]
    public Guid SkuId { get; set; }
    
    [Range(1, int.MaxValue)]
    public int Quantity { get; set; }
    
    [Range(0.01, double.MaxValue)]
    public decimal? UnitPrice { get; set; }
}

public class OrderLineItemResponseDto
{
    public Guid Id { get; set; }
    public Guid SkuId { get; set; }
    public int Quantity { get; set; }
    public decimal UnitPrice { get; set; }
    public decimal TotalPrice { get; set; }
    public string ProductName { get; set; } = string.Empty;
    public string SkuCode { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
}

public class OrderCreateDto
{
    [Required]
    [EmailAddress]
    public string CustomerEmail { get; set; } = string.Empty;
    
    public string? CustomerName { get; set; }
    
    [Range(0, double.MaxValue)]
    public decimal TaxAmount { get; set; } = 0;
    
    [Range(0, double.MaxValue)]
    public decimal ShippingAmount { get; set; } = 0;
    
    [Required]
    [StringLength(3, MinimumLength = 3)]
    public string Currency { get; set; } = "USD";

    public string? Notes { get; set; }

    public Guid? FlashSaleCampaignId { get; set; }

    [Required]
    [MinLength(1)]
    public List<OrderLineItemCreateDto> LineItems { get; set; } = new();
}

public class OrderUpdateDto
{
    public string? CustomerName { get; set; }
    public OrderStatus? Status { get; set; }
    public string? Notes { get; set; }
}

public class OrderResponseDto
{
    public Guid Id { get; set; }
    public string OrderNumber { get; set; } = string.Empty;
    public string CustomerEmail { get; set; } = string.Empty;
    public string? CustomerName { get; set; }
    public decimal Subtotal { get; set; }
    public decimal TaxAmount { get; set; }
    public decimal ShippingAmount { get; set; }
    public decimal TotalAmount { get; set; }
    public string Currency { get; set; } = string.Empty;
    public OrderStatus Status { get; set; }
    public string? Notes { get; set; }
    public Guid? FlashSaleCampaignId { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    public List<OrderLineItemResponseDto> LineItems { get; set; } = new();
}

public class PaymentCreateDto
{
    [Required]
    [Range(0.01, double.MaxValue)]
    public decimal Amount { get; set; }
    
    [Required]
    [StringLength(3, MinimumLength = 3)]
    public string Currency { get; set; } = "USD";
    
    [Required]
    [MinLength(1)]
    public string PaymentMethod { get; set; } = string.Empty;
    
    public string? ReferenceNumber { get; set; }
    public string? Notes { get; set; }
}

public class PaymentResponseDto
{
    public Guid Id { get; set; }
    public Guid OrderId { get; set; }
    public decimal Amount { get; set; }
    public string Currency { get; set; } = string.Empty;
    public string PaymentMethod { get; set; } = string.Empty;
    public string? GatewayTransactionId { get; set; }
    public PaymentStatus Status { get; set; }
    public string? ReferenceNumber { get; set; }
    public string? Notes { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}
