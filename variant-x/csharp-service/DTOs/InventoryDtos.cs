using System.ComponentModel.DataAnnotations;

namespace FlashSale.Api.DTOs;

public class InventoryUpdateDto
{
    [Range(0, int.MaxValue)]
    public int? Quantity { get; set; }
    
    public bool? AllowNegativeStock { get; set; }
}

public class InventoryResponseDto
{
    public Guid Id { get; set; }
    public Guid SkuId { get; set; }
    public int Quantity { get; set; }
    public int ReservedQuantity { get; set; }
    public int AvailableQuantity { get; set; }
    public bool AllowNegativeStock { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}

public class InventoryAdjustmentDto
{
    [Required]
    public int Adjustment { get; set; }
    
    public string Reason { get; set; } = "Manual adjustment";
}
