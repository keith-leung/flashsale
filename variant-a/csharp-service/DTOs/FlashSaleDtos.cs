using System.ComponentModel.DataAnnotations;
using FlashSale.Api.Models;

namespace FlashSale.Api.DTOs;

public class FlashSaleEventCreateDto
{
    [Required]
    [StringLength(250, MinimumLength = 1)]
    public string Name { get; set; } = string.Empty;
    
    public string? Description { get; set; }
    
    [Required]
    public Guid SkuId { get; set; }
    
    [Required]
    [Range(1, int.MaxValue)]
    public int TotalSaleLimit { get; set; }
    
    [Range(1, int.MaxValue)]
    public int MaxQuantityPerCustomer { get; set; } = 1;
    
    [Required]
    public DateTime StartTime { get; set; }
    
    [Required]
    public DateTime EndTime { get; set; }
    
    public bool IsActive { get; set; } = true;
    
    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
    {
        if (EndTime <= StartTime)
        {
            yield return new ValidationResult("EndTime must be after StartTime", 
                new[] { nameof(EndTime) });
        }
    }
}

public class FlashSaleEventUpdateDto
{
    [StringLength(250, MinimumLength = 1)]
    public string? Name { get; set; }
    
    public string? Description { get; set; }
    
    [Range(1, int.MaxValue)]
    public int? TotalSaleLimit { get; set; }
    
    [Range(1, int.MaxValue)]
    public int? MaxQuantityPerCustomer { get; set; }
    
    public DateTime? StartTime { get; set; }
    
    public DateTime? EndTime { get; set; }
    
    public bool? IsActive { get; set; }
}

public class FlashSaleEventResponseDto
{
    public Guid Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public Guid SkuId { get; set; }
    public int TotalSaleLimit { get; set; }
    public int SoldQuantity { get; set; }
    public int RemainingQuantity { get; set; }
    public int MaxQuantityPerCustomer { get; set; }
    public DateTime StartTime { get; set; }
    public DateTime EndTime { get; set; }
    public FlashSaleStatus Status { get; set; }
    public bool IsTimeActive { get; set; }
    public bool IsAvailable { get; set; }
    public bool IsActive { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}

// =============================================================================
// DEPRECATED - DO NOT USE (Violates Policy 6)
// =============================================================================
// Flash sale purchases MUST go through /api/v1/orders endpoint
// Backend intelligently detects if SKU is in active flash sale
// These DTOs are kept to avoid breaking imports but should NOT be used
// =============================================================================

/// <summary>
/// DEPRECATED: Use /api/v1/orders endpoint instead (Policy 6)
/// </summary>
[Obsolete("Use /api/v1/orders endpoint instead (Policy 6)")]
public class PurchaseRequestDto
{
    [Required]
    [Range(1, int.MaxValue)]
    public int Quantity { get; set; }

    public string? CustomerId { get; set; }
}

/// <summary>
/// DEPRECATED: Use /api/v1/orders endpoint instead (Policy 6)
/// </summary>
[Obsolete("Use /api/v1/orders endpoint instead (Policy 6)")]
public class PurchaseResponseDto
{
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
    public Guid FlashSaleId { get; set; }
    public int QuantityPurchased { get; set; }
    public int RemainingQuantity { get; set; }
}
