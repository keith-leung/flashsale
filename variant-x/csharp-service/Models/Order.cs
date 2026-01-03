using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace FlashSale.Api.Models;

public enum OrderStatus
{
    Pending,
    Confirmed,
    Processing,
    Shipped,
    Delivered,
    Cancelled,
    Refunded
}

public enum PaymentStatus
{
    Pending,
    Authorized,
    Captured,
    Failed,
    Cancelled,
    Refunded
}

/// <summary>
/// Order model for both regular and flash sale orders
/// </summary>
[Table("orders")]
public class Order : BaseEntity
{
    [Required]
    [StringLength(50)]
    public string OrderNumber { get; set; } = string.Empty;
    
    // Customer information
    [Required]
    [StringLength(255)]
    public string CustomerEmail { get; set; } = string.Empty;
    
    [StringLength(255)]
    public string? CustomerName { get; set; }
    
    // Order totals
    [Column(TypeName = "decimal(10,2)")]
    public decimal Subtotal { get; set; }
    
    [Column(TypeName = "decimal(10,2)")]
    public decimal TaxAmount { get; set; } = 0;
    
    [Column(TypeName = "decimal(10,2)")]
    public decimal ShippingAmount { get; set; } = 0;
    
    [Column(TypeName = "decimal(10,2)")]
    public decimal TotalAmount { get; set; }
    
    [Required]
    [StringLength(3)]
    public string Currency { get; set; } = "USD";
    
    // Status and metadata
    public OrderStatus Status { get; set; } = OrderStatus.Pending;

    public string? Notes { get; set; }

    // Flash sale campaign reference (optional) - SACRED schema compliant
    [Column("flash_sale_campaign_id")]
    public Guid? FlashSaleCampaignId { get; set; }

    // Navigation properties
    public FlashSale? FlashSaleCampaign { get; set; }
    public ICollection<OrderLineItem> LineItems { get; set; } = new List<OrderLineItem>();
    public ICollection<Payment> Payments { get; set; } = new List<Payment>();
}

/// <summary>
/// Individual items within an order
/// </summary>
[Table("order_line_items")]
public class OrderLineItem : BaseEntity
{
    [Required]
    public Guid OrderId { get; set; }
    
    [Required]
    public Guid SkuId { get; set; }
    
    // Item details
    [Range(1, int.MaxValue)]
    public int Quantity { get; set; }
    
    [Column(TypeName = "decimal(10,2)")]
    public decimal UnitPrice { get; set; }
    
    [Column(TypeName = "decimal(10,2)")]
    public decimal TotalPrice { get; set; }
    
    // Product snapshot (in case SKU details change)
    [Required]
    [StringLength(255)]
    public string ProductName { get; set; } = string.Empty;
    
    [Required]
    [StringLength(255)]
    public string SkuCode { get; set; } = string.Empty;
    
    // Navigation properties
    public Order Order { get; set; } = null!;
    public Sku Sku { get; set; } = null!;
}

/// <summary>
/// Payment transactions for orders
/// </summary>
[Table("payments")]
public class Payment : BaseEntity
{
    [Required]
    public Guid OrderId { get; set; }
    
    // Payment details
    [Column(TypeName = "decimal(10,2)")]
    public decimal Amount { get; set; }
    
    [Required]
    [StringLength(3)]
    public string Currency { get; set; } = "USD";
    
    [Required]
    [StringLength(50)]
    public string PaymentMethod { get; set; } = string.Empty; // credit_card, paypal, etc.
    
    // Payment gateway information
    [StringLength(255)]
    public string? GatewayTransactionId { get; set; }
    
    public string? GatewayResponse { get; set; } // JSON response from gateway
    
    // Status and metadata
    public PaymentStatus Status { get; set; } = PaymentStatus.Pending;
    
    [StringLength(100)]
    public string? ReferenceNumber { get; set; }
    
    public string? Notes { get; set; }
    
    // Navigation property
    public Order Order { get; set; } = null!;
}
